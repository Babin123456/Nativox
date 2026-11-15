#!/usr/bin/env python3
"""
main.py - Voice feature extractor / preserver

Extracts the characteristics of a speaker's voice (pitch, timbre, formants,
loudness, voice quality, rhythm, emotion, speaker embedding) from an audio file
and stores them in an easy-to-read JSON "voice profile".

It also prepares clean reference material for voice cloning (XTTS, OpenVoice...):
    voice_profile.json              all extracted features
    voice_profile_reference.wav     best ~30 s of clean speech (silence removed)
    voice_profile_clips/clip_*.wav  several clean 6-12 s clips (better cloning)
    voice_profile_energy.png        energy + pitch graph of the original voice
    voice_profile_background.wav    the original BACKGROUND sound (music / noise / ambience),
                                    kept untouched so test_cloned.py can put it back
    voice_profile_vocals.wav        the original voice only (used for analysis + cloning clips)

Background preservation: the recording is split with Demucs into voice + background.
The voice features and cloning clips are taken from the clean voice stem (so the
background does not pollute the clone), and the background stem is saved as-is.

Usage:
    1. Set AUDIO_PATH below (mp3 or wav).
    2. Run:  python main.py

Install:
    pip install numpy librosa soundfile scipy matplotlib
    pip install praat-parselmouth        # formants, jitter, shimmer, HNR (recommended)
    pip install demucs torch torchaudio  # separates voice from background (first run downloads ~80 MB)
    pip install noisereduce              # gentle noise removal for the reference (recommended)
    pip install resemblyzer              # speaker embedding   (optional)
    pip install transformers torch       # neural emotion model (optional)

Tip: the cleaner and longer (30-60 s) the source recording, the closer the clone.
Only use this on voices you own or have explicit consent to clone.
"""

import glob
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone

import numpy as np

try:
    import librosa
    import soundfile as sf
    from scipy import signal
    from scipy.ndimage import uniform_filter1d
except ImportError:
    sys.exit("Missing dependencies. Run: pip install numpy librosa soundfile scipy matplotlib")

try:
    import parselmouth
    from parselmouth.praat import call
    HAS_PARSELMOUTH = True
except ImportError:
    HAS_PARSELMOUTH = False

# =========================================================================== #
# SETTINGS - edit these, then just run:  python main.py
# =========================================================================== #
AUDIO_PATH = r"D:/VS Code/Nativox/Dubbing/08_Voice_extraction_translation/test2.mp3"   # <-- your .mp3 / .wav
OUTPUT_JSON = "voice_profile.json"       # JSON file that will be created
CLIPS_DIR = "voice_profile_clips"        # folder for the clean reference clips
USE_EMOTION_MODEL = False                # True = neural emotion model (needs transformers + torch)
USE_SPEAKER_EMBEDDING = False            # True = speaker embedding (needs resemblyzer)
USE_DENOISE = True                       # gentle noise reduction (needs noisereduce; skipped if missing)
PRESERVE_BACKGROUND = True               # split voice / background (Demucs) and keep the background untouched
                                         # (or run:  python main.py --no-background)

REF_MAX_SEC = 30        # length of voice_profile_reference.wav
MAX_REF_CLIPS = 6       # how many clean clips to keep for cloning
CLIP_TARGET_SEC = 9     # approximate length of each clip
# =========================================================================== #

SR = 22050  # analysis / reference sample rate


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def clean(value):
    """Make values JSON-safe (numpy types, NaN, inf)."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def stats(x, prefix=""):
    """Summary statistics of a 1-D array (NaNs ignored)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if x.size == 0:
        return {f"{prefix}mean": None}
    return {
        f"{prefix}mean": np.mean(x),
        f"{prefix}median": np.median(x),
        f"{prefix}std": np.std(x),
        f"{prefix}min": np.min(x),
        f"{prefix}max": np.max(x),
        f"{prefix}p5": np.percentile(x, 5),
        f"{prefix}p95": np.percentile(x, 95),
    }


def hz_to_note(hz):
    if not hz or hz <= 0:
        return None
    return librosa.hz_to_note(hz)


def downsample(arr, n=100):
    """Reduce a contour to n points so the JSON stays readable."""
    arr = np.asarray(arr, dtype=float)
    if arr.size <= n:
        return arr
    idx = np.linspace(0, arr.size - 1, n).astype(int)
    return arr[idx]


def active_db_mean(y):
    """Mean loudness (dB) over the active (speech) frames only, ignoring pauses."""
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
    active = db[db > np.percentile(db, 95) - 25]
    return float(np.mean(active)) if active.size else float(np.mean(db))


# --------------------------------------------------------------------------- #
# loading + cleaning
# --------------------------------------------------------------------------- #
def highpass(y, sr, cutoff=70):
    """Remove rumble / DC below the voice range."""
    sos = signal.butter(4, cutoff, btype="highpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y).astype(np.float32)


def denoise(y, sr):
    try:
        import noisereduce as nr
    except ImportError:
        print("  (tip: pip install noisereduce  -> cleaner reference audio, better cloning)")
        return y, False
    out = nr.reduce_noise(y=y, sr=sr, stationary=True, prop_decrease=0.6)
    return out.astype(np.float32), True


def load_audio(path):
    y, sr = librosa.load(path, sr=SR, mono=True)
    if y.size == 0:
        sys.exit("Audio file is empty.")
    y, _ = librosa.effects.trim(y, top_db=35)          # strip leading/trailing silence
    y = highpass(y, sr)
    denoised = False
    if USE_DENOISE:
        y, denoised = denoise(y, sr)
    peak = np.max(np.abs(y)) or 1.0
    y = (y / peak * 0.95).astype(np.float32)            # peak-normalize
    return y, sr, denoised


# --------------------------------------------------------------------------- #
# clean reference clips for cloning
# --------------------------------------------------------------------------- #
def speech_segments(y, sr, top_db=32, merge_gap=0.35, min_len=0.25):
    iv = librosa.effects.split(y, top_db=top_db, frame_length=2048, hop_length=256)
    merged = []
    for s, e in iv:
        if merged and (s - merged[-1][1]) / sr < merge_gap:
            merged[-1][1] = int(e)
        else:
            merged.append([int(s), int(e)])
    return [(s, e) for s, e in merged if (e - s) / sr >= min_len]


def _fade(y, sr, ms=10):
    n = int(sr * ms / 1000)
    if len(y) > 2 * n:
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        y = y.copy()
        y[:n] *= ramp
        y[-n:] *= ramp[::-1]
    return y


def build_clips(y, sr):
    """Cut the recording into clean speech-only clips at natural pauses."""
    pad = int(0.06 * sr)
    gap = np.zeros(int(0.15 * sr), dtype=np.float32)
    clips, cur, cur_len = [], [], 0.0

    def flush():
        pieces = []
        for p in cur:
            pieces += [p, gap]
        return np.concatenate(pieces[:-1])

    for s, e in speech_segments(y, sr):
        piece = y[max(0, s - pad): min(len(y), e + pad)]
        cur.append(piece)
        cur_len += len(piece) / sr
        if cur_len >= CLIP_TARGET_SEC:
            clips.append(flush())
            cur, cur_len = [], 0.0
    if cur and (cur_len >= 3.0 or not clips):
        clips.append(flush())
    return clips or [y]


def prepare_reference(y, sr):
    """Pick the clearest clips; write clips + one combined reference wav."""
    clips = build_clips(y, sr)
    scored = sorted(range(len(clips)), key=lambda i: active_db_mean(clips[i]), reverse=True)
    keep = sorted(scored[:MAX_REF_CLIPS])               # best clips, original order
    chosen = []
    for i in keep:
        c = clips[i]
        c = _fade((c / (np.max(np.abs(c)) or 1.0) * 0.95).astype(np.float32), sr)
        chosen.append(c)

    # combined reference (capped length)
    gap = np.zeros(int(0.25 * sr), dtype=np.float32)
    ref, total = [], 0.0
    for c in chosen:
        if total >= REF_MAX_SEC:
            break
        ref += [c, gap]
        total += len(c) / sr + 0.25
    reference = np.concatenate(ref[:-1])[: int(REF_MAX_SEC * sr)]
    return chosen, reference


def save_reference_files(chosen, reference, sr, ref_path, clips_dir=None):
    c_dir = clips_dir or CLIPS_DIR
    os.makedirs(c_dir, exist_ok=True)
    for old in glob.glob(os.path.join(c_dir, "clip_*.wav")):
        try:
            os.remove(old)
        except Exception:
            pass
    info = []
    for i, c in enumerate(chosen, 1):
        p = os.path.join(c_dir, f"clip_{i:02d}.wav")
        sf.write(p, c, sr)
        info.append({"file": p.replace("\\", "/"), "duration_sec": len(c) / sr,
                     "speech_loudness_db": active_db_mean(c)})
    sf.write(ref_path, reference, sr)
    return info


# --------------------------------------------------------------------------- #
# feature groups
# --------------------------------------------------------------------------- #
def extract_pitch(y, sr):
    f0, voiced_flag, _ = librosa.pyin(
        y, fmin=65, fmax=500, sr=sr, frame_length=2048, hop_length=256
    )
    voiced = f0[~np.isnan(f0)]
    out = {"voiced_ratio": float(np.mean(~np.isnan(f0)))}
    if voiced.size == 0:
        out["note"] = "No voiced frames detected"
        return out, f0

    out.update(stats(voiced, "f0_hz_"))
    out["f0_mean_note"] = hz_to_note(float(np.mean(voiced)))
    out["f0_range_semitones"] = float(12 * np.log2(np.percentile(voiced, 95) / np.percentile(voiced, 5)))
    semis = 12 * np.log2(voiced / np.median(voiced))
    out["intonation_variability_semitone_std"] = float(np.std(semis))
    out["pitch_slope_hz_per_sec"] = float(
        np.polyfit(np.arange(voiced.size) * 256 / sr, voiced, 1)[0]
    ) if voiced.size > 2 else None
    out["f0_contour_hz_downsampled"] = np.where(np.isnan(downsample(f0)), None, downsample(f0)).tolist()
    return out, f0


def extract_energy(y, sr):
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
    out = {}
    out.update(stats(rms, "rms_"))
    out.update(stats(db, "loudness_db_"))
    out["speech_loudness_db_mean"] = active_db_mean(y)   # used by test_translate.py
    out["dynamic_range_db"] = float(np.percentile(db, 95) - np.percentile(db, 5))
    out["energy_contour_downsampled"] = downsample(rms).tolist()
    return out, rms


def extract_timbre(y, sr):
    out = {}
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    out["mfcc_mean"] = np.mean(mfcc, axis=1)
    out["mfcc_std"] = np.std(mfcc, axis=1)
    delta = librosa.feature.delta(mfcc)
    out["mfcc_delta_mean"] = np.mean(delta, axis=1)

    for name, feat in {
        "spectral_centroid_hz": librosa.feature.spectral_centroid(y=y, sr=sr)[0],
        "spectral_bandwidth_hz": librosa.feature.spectral_bandwidth(y=y, sr=sr)[0],
        "spectral_rolloff_hz": librosa.feature.spectral_rolloff(y=y, sr=sr)[0],
        "spectral_flatness": librosa.feature.spectral_flatness(y=y)[0],
        "zero_crossing_rate": librosa.feature.zero_crossing_rate(y)[0],
    }.items():
        out[name] = {"mean": float(np.mean(feat)), "std": float(np.std(feat))}

    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    out["spectral_contrast_mean"] = np.mean(contrast, axis=1)

    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=80)
    out["log_mel_mean"] = np.mean(librosa.power_to_db(mel), axis=1)  # 80-band voice "fingerprint"
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    out["chroma_mean"] = np.mean(chroma, axis=1)

    cent = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    out["brightness_label"] = "dark/warm" if cent < 1500 else "balanced" if cent < 2500 else "bright"
    return out


def extract_praat(path):
    """Formants, jitter, shimmer, HNR via Praat (parselmouth)."""
    if not HAS_PARSELMOUTH:
        return {"available": False, "note": "pip install praat-parselmouth for formants/jitter/shimmer/HNR"}
    try:
        snd = parselmouth.Sound(path)
        if snd.n_channels > 1:
            snd = snd.convert_to_mono()
        pitch = snd.to_pitch(pitch_floor=65, pitch_ceiling=500)
        pp = call([snd, pitch], "To PointProcess (cc)")

        out = {"available": True}
        out["jitter_local"] = call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        out["jitter_rap"] = call(pp, "Get jitter (rap)", 0, 0, 0.0001, 0.02, 1.3)
        out["shimmer_local"] = call([snd, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        out["shimmer_apq3"] = call([snd, pp], "Get shimmer (apq3)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        harm = snd.to_harmonicity()
        out["hnr_db"] = call(harm, "Get mean", 0, 0)

        formant = snd.to_formant_burg(max_number_of_formants=5, maximum_formant=5500)
        times = pitch.xs()
        f0_vals = pitch.selected_array["frequency"]
        voiced_t = times[f0_vals > 0]
        formants = {}
        for i in range(1, 5):
            vals = [formant.get_value_at_time(i, t) for t in voiced_t]
            vals = np.array([v for v in vals if v is not None and not np.isnan(v)])
            formants[f"F{i}_hz"] = {"median": np.median(vals), "std": np.std(vals)} if vals.size else None
        out["formants"] = formants
        return out
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def extract_rhythm(y, sr):
    intervals = librosa.effects.split(y, top_db=30)
    total = len(y) / sr
    speech = sum((e - s) for s, e in intervals) / sr
    pauses = [(intervals[i + 1][0] - intervals[i][1]) / sr for i in range(len(intervals) - 1)]
    pauses = [p for p in pauses if p > 0.15]

    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    out = {
        "total_duration_sec": total,
        "speech_duration_sec": speech,
        "speech_ratio": speech / total if total else None,
        "pause_count": len(pauses),
        "pause_mean_sec": float(np.mean(pauses)) if pauses else 0.0,
        "pause_max_sec": float(np.max(pauses)) if pauses else 0.0,
        "syllable_like_onsets_per_sec": len(onsets) / speech if speech else None,
    }
    rate = out["syllable_like_onsets_per_sec"]
    if rate is not None:
        out["speaking_pace_label"] = "slow" if rate < 3 else "moderate" if rate < 5.5 else "fast"
    return out


# --------------------------------------------------------------------------- #
# emotion + tone
# --------------------------------------------------------------------------- #
def heuristic_emotion(pitch, energy, rhythm):
    """Rough prosody-based arousal estimate (not a trained classifier)."""
    score = 0.0
    n = 0
    if pitch.get("intonation_variability_semitone_std") is not None:
        score += min(pitch["intonation_variability_semitone_std"] / 4.0, 1.5); n += 1
    if energy.get("dynamic_range_db") is not None:
        score += min(energy["dynamic_range_db"] / 40.0, 1.5); n += 1
    if rhythm.get("syllable_like_onsets_per_sec"):
        score += min(rhythm["syllable_like_onsets_per_sec"] / 5.0, 1.5); n += 1
    arousal = score / n if n else None
    label = None
    if arousal is not None:
        label = "calm / subdued" if arousal < 0.55 else "neutral / conversational" if arousal < 0.95 else "energetic / expressive"
    return {"method": "prosody heuristic", "arousal_score": arousal, "tone_label": label}


def neural_emotion(path):
    try:
        from transformers import pipeline
        clf = pipeline("audio-classification", model="superb/wav2vec2-base-superb-er")
        res = clf(path, top_k=4)
        names = {"neu": "neutral", "hap": "happy", "ang": "angry", "sad": "sad"}
        return {
            "method": "wav2vec2-base-superb-er",
            "scores": {names.get(r["label"], r["label"]): r["score"] for r in res},
            "dominant": names.get(res[0]["label"], res[0]["label"]),
        }
    except Exception as exc:
        return {"method": "wav2vec2-base-superb-er", "error": f"unavailable: {exc}"}


def speaker_embedding(path):
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav
        wav = preprocess_wav(path)
        emb = VoiceEncoder().embed_utterance(wav)
        return {"model": "resemblyzer", "dim": int(emb.size), "vector": emb}
    except Exception as exc:
        return {"error": f"unavailable (pip install resemblyzer): {exc}"}


# --------------------------------------------------------------------------- #
# energy graph
# --------------------------------------------------------------------------- #
def save_energy_graph(y, sr, f0, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hop = 256
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    db = np.maximum(librosa.amplitude_to_db(rms + 1e-9), -80.0)
    db_s = uniform_filter1d(db, size=7)
    t = librosa.times_like(rms, sr=sr, hop_length=hop)
    tw = np.arange(len(y)) / sr
    speech_db = active_db_mean(y)

    fig, ax = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    ax[0].plot(tw, y, lw=0.4, color="#4C72B0")
    ax[0].set_ylabel("Amplitude")
    ax[0].set_title(title, fontsize=13, fontweight="bold")

    ax[1].fill_between(t, -80, db_s, color="#C44E52", alpha=0.25)
    ax[1].plot(t, db, color="#B0B0B0", lw=0.7, label="frame energy")
    ax[1].plot(t, db_s, color="#C44E52", lw=1.6, label="smoothed energy")
    ax[1].axhline(speech_db, ls="--", color="black", lw=0.9, label=f"speech mean {speech_db:.1f} dB")
    ax[1].set_ylabel("Energy (dB)")
    ax[1].set_ylim(-80, 0)
    ax[1].legend(loc="lower right", fontsize=8)

    tf = librosa.times_like(f0, sr=sr, hop_length=hop)
    ax[2].plot(tf, f0, ".", ms=2.5, color="#55A868")
    ax[2].set_ylabel("Pitch F0 (Hz)")
    ax[2].set_xlabel("Time (s)")

    for a in ax:
        a.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# background preservation (Demucs source separation)
# --------------------------------------------------------------------------- #
BG_SR = 44100  # background / voice stems are stored at this rate (Demucs native), lossless float WAV


def _source_signature(path):
    st = os.stat(path)
    return {"source": os.path.abspath(path), "size": st.st_size, "mtime": st.st_mtime}


def separate_stems(path, bg_path, vocals_path):
    """Split the recording into background + voice with Demucs (cached on disk).

    The cache is keyed on the source file (path, size, modified time), so a different
    input never reuses old stems. Returns info about the stems for the voice profile.
    """
    sidecar = bg_path + ".json"
    sig = _source_signature(path)
    cached = False
    if os.path.isfile(bg_path) and os.path.isfile(vocals_path) and os.path.isfile(sidecar):
        try:
            with open(sidecar, "r", encoding="utf-8") as f:
                cached = json.load(f) == sig
        except Exception:
            cached = False

    if cached:
        print("  Using cached voice / background stems.")
    else:
        try:
            import torch
            from demucs.pretrained import get_model
            from demucs.apply import apply_model
        except ImportError as exc:
            sys.exit(f"Background preservation needs Demucs: {exc}\n"
                     "Run: pip install demucs torch torchaudio\n"
                     "(or run without it:  python main.py --no-background)")

        print("  Separating voice and background with Demucs (first run downloads ~80 MB) ...")
        orig_load = torch.load          # Demucs checkpoints need weights_only=False on torch >= 2.6
        torch.load = lambda *a, **k: orig_load(*a, **{**k, "weights_only": k.get("weights_only", False)})
        try:
            model = get_model("htdemucs")
        finally:
            torch.load = orig_load
        model.eval()
        m_sr = int(model.samplerate)

        y, _ = librosa.load(path, sr=m_sr, mono=False)
        y = np.stack([y, y]) if y.ndim == 1 else (np.repeat(y, 2, 0) if y.shape[0] == 1 else y[:2])
        wav = torch.from_numpy(np.ascontiguousarray(y)).float()
        std = float(wav.mean(0).std()) or 1.0

        device = "cuda" if torch.cuda.is_available() else "cpu"
        with torch.no_grad():
            src = apply_model(model, (wav / std)[None], device=device,
                              split=True, overlap=0.25, progress=True)[0] * std
        names = list(model.sources)
        v = names.index("vocals")
        vocals = src[v]
        background = sum(src[i] for i in range(len(names)) if i != v)   # drums + bass + other
        del model
        if device == "cuda":
            torch.cuda.empty_cache()

        for p, arr in ((bg_path, background), (vocals_path, vocals)):
            a = arr.cpu().numpy().astype(np.float32)                    # (2, T)
            if m_sr != BG_SR:
                a = librosa.resample(a, orig_sr=m_sr, target_sr=BG_SR)
            sf.write(p, a.T, BG_SR, subtype="FLOAT")                    # lossless
        with open(sidecar, "w", encoding="utf-8") as f:
            json.dump(sig, f)

    vo, _ = sf.read(vocals_path, dtype="float32", always_2d=True)
    voice_db = active_db_mean(librosa.resample(vo.mean(axis=1), orig_sr=BG_SR, target_sr=SR))
    return {
        "enabled": True,
        "separation_model": "htdemucs",
        "original_audio": os.path.abspath(path),
        "background_wav": bg_path.replace("\\", "/"),
        "vocals_wav": vocals_path.replace("\\", "/"),
        "sample_rate": BG_SR,
        "duration_sec": sf.info(bg_path).frames / BG_SR,
        # loudness of the voice inside the original recording (unnormalised) - lets
        # test_cloned.py keep the same voice-to-background balance
        "voice_level_db_in_original": voice_db,
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_profile(input_path, ref_path, use_emotion=False, use_embedding=False, clips_dir=None,
                  source_name=None, background=None):
    y, sr, denoised = load_audio(input_path)

    chosen, reference = prepare_reference(y, sr)
    clip_info = save_reference_files(chosen, reference, sr, ref_path, clips_dir=clips_dir)

    pitch, f0 = extract_pitch(y, sr)
    energy, _ = extract_energy(y, sr)
    timbre = extract_timbre(y, sr)
    rhythm = extract_rhythm(y, sr)

    with tempfile.TemporaryDirectory() as td:           # Praat reads from a file
        tmp = os.path.join(td, "full.wav")
        sf.write(tmp, y, sr)
        praat = extract_praat(tmp)

    emotion = {"heuristic": heuristic_emotion(pitch, energy, rhythm)}
    if use_emotion:
        emotion["neural"] = neural_emotion(ref_path)

    c_dir = clips_dir or CLIPS_DIR
    profile = {
        "metadata": {
            "source_file": source_name or os.path.basename(input_path),
            "reference_audio": os.path.basename(ref_path),
            "sample_rate": sr,
            "duration_sec": len(y) / sr,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "tools": {"librosa": librosa.__version__, "parselmouth": HAS_PARSELMOUTH},
        },
        "reference_preparation": {
            "highpass_hz": 70,
            "denoised": denoised,
            "reference_duration_sec": len(reference) / sr,
            "clip_count": len(clip_info),
            "clips": clip_info,
        },
        "pitch": pitch,
        "energy_loudness": energy,
        "timbre": timbre,
        "voice_quality_and_formants": praat,
        "rhythm_and_pace": rhythm,
        "emotion_and_tone": emotion,
    }
    profile["background"] = background or {"enabled": False}
    if use_embedding:
        profile["speaker_embedding"] = speaker_embedding(ref_path)
    return profile, y, sr, f0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Voice feature extractor / preserver")
    parser.add_argument("audio_path", nargs="?", default=AUDIO_PATH, help="Path to input audio file")
    parser.add_argument("--output-json", default=OUTPUT_JSON, help="Path for output voice_profile.json")
    parser.add_argument("--clips-dir", default=CLIPS_DIR, help="Folder for clean reference clips")
    parser.add_argument("--no-background", action="store_true",
                        help="Skip voice/background separation (background will not be preserved)")
    args = parser.parse_args()

    audio_path = args.audio_path
    output_json = args.output_json
    clips_dir = args.clips_dir

    if not os.path.isfile(audio_path):
        sys.exit(f"Audio file not found: {audio_path}\nEdit AUDIO_PATH at the top of main.py or provide path via argument.")

    base = os.path.splitext(output_json)[0]
    ref_path = base + "_reference.wav"
    graph_path = base + "_energy.png"
    bg_path = base + "_background.wav"
    vocals_path = base + "_vocals.wav"

    analysis_path, background = audio_path, None
    if PRESERVE_BACKGROUND and not args.no_background:
        print(f"Separating voice and background: {audio_path} ...")
        background = separate_stems(audio_path, bg_path, vocals_path)
        analysis_path = vocals_path          # analyse + build cloning clips from the clean voice only

    print(f"Analyzing: {analysis_path} ...")
    profile, y, sr, f0 = build_profile(analysis_path, ref_path, USE_EMOTION_MODEL, USE_SPEAKER_EMBEDDING,
                                       clips_dir=clips_dir, source_name=os.path.basename(audio_path),
                                       background=background)

    try:
        save_energy_graph(y, sr, f0, graph_path, f"Original voice - energy & pitch ({os.path.basename(audio_path)})")
    except Exception as exc:
        print(f"  (energy graph skipped: {exc})")
    profile["files"] = {"reference_wav": ref_path, "clips_dir": clips_dir, "energy_graph": graph_path}
    if background:
        profile["files"]["background_wav"] = bg_path
        profile["files"]["vocals_wav"] = vocals_path

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(clean(profile), f, indent=2, ensure_ascii=False)

    print(f"Voice profile saved : {output_json}")
    print(f"Reference audio     : {ref_path}")
    print(f"Reference clips     : {clips_dir}/ ({profile['reference_preparation']['clip_count']} clips)")
    print(f"Energy graph        : {graph_path}")
    if background:
        print(f"Background (kept)   : {bg_path}")
        print(f"Voice only          : {vocals_path}")


if __name__ == "__main__":
    main()