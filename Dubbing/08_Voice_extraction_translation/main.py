#!/usr/bin/env python3
"""
main.py - Voice feature extractor / preserver

Extracts the characteristics of a speaker's voice (pitch, timbre, formants,
loudness, voice quality, rhythm, emotion, speaker embedding) from an audio file
and stores them in an easy-to-read JSON "voice profile". A cleaned, normalized
reference WAV is saved next to it so that a voice-cloning / TTS system
(XTTS, OpenVoice, Tortoise, StyleTTS2, etc.) can use both the audio and the
features.

Usage:
    1. Set AUDIO_PATH at the top of this file (mp3 or wav).
    2. Run:  python main.py

Install:
    pip install numpy librosa soundfile scipy
    pip install praat-parselmouth        # formants, jitter, shimmer, HNR (recommended)
    pip install resemblyzer              # speaker embedding   (optional, --embedding)
    pip install transformers torch       # neural emotion model (optional, --emotion)

Only use this on voices you own or have explicit consent to clone.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

try:
    import librosa
    import soundfile as sf
except ImportError:
    sys.exit("Missing dependencies. Run: pip install numpy librosa soundfile scipy")

try:
    import importlib
    parselmouth = importlib.import_module("parselmouth")
    call = getattr(importlib.import_module("parselmouth.praat"), "call")
    HAS_PARSELMOUTH = True
except (ImportError, ModuleNotFoundError, Exception):
    HAS_PARSELMOUTH = False

# =========================================================================== #
# SETTINGS - edit these or pass as CLI arguments: python main.py [audio_path] [output_json]
# =========================================================================== #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CANDIDATE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "tests", "test2.mp4"))
AUDIO_PATH = DEFAULT_CANDIDATE if os.path.isfile(DEFAULT_CANDIDATE) else "test.mp3"
OUTPUT_JSON = "voice_profile.json"       # JSON file that will be created
USE_EMOTION_MODEL = False                # True = neural emotion model (needs transformers + torch)
USE_SPEAKER_EMBEDDING = False            # True = speaker embedding (needs resemblyzer)
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


# --------------------------------------------------------------------------- #
# loading + preserving reference audio
# --------------------------------------------------------------------------- #
def load_audio(path):
    y, sr = librosa.load(path, sr=SR, mono=True)
    if y.size == 0:
        sys.exit("Audio file is empty.")
    y, _ = librosa.effects.trim(y, top_db=35)          # strip leading/trailing silence
    peak = np.max(np.abs(y)) or 1.0
    y = (y / peak * 0.95).astype(np.float32)            # peak-normalize
    return y, sr


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
    # intonation: how much the pitch moves between consecutive voiced frames
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

    # brightness label
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
    except Exception as exc:  # keep going even if Praat fails on odd audio
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
    sr_rate = out["syllable_like_onsets_per_sec"]
    if sr_rate is not None:
        out["speaking_pace_label"] = "slow" if sr_rate < 3 else "moderate" if sr_rate < 5.5 else "fast"
    return out


# --------------------------------------------------------------------------- #
# emotion + tone
# --------------------------------------------------------------------------- #
def heuristic_emotion(pitch, energy, rhythm):
    """Rough prosody-based arousal estimate (not a trained classifier)."""
    score = 0.0
    n = 0
    if pitch.get("f0_hz_std") is not None:
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


# --------------------------------------------------------------------------- #
# speaker embedding
# --------------------------------------------------------------------------- #
def speaker_embedding(path):
    try:
        import importlib
        resemblyzer = importlib.import_module("resemblyzer")
        VoiceEncoder = getattr(resemblyzer, "VoiceEncoder")
        preprocess_wav = getattr(resemblyzer, "preprocess_wav")
        wav = preprocess_wav(path)
        emb = VoiceEncoder().embed_utterance(wav)
        return {"model": "resemblyzer", "dim": int(emb.size), "vector": emb}
    except Exception as exc:
        return {"error": f"unavailable (pip install resemblyzer): {exc}"}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_profile(input_path, ref_path, use_emotion, use_embedding):
    y, sr = load_audio(input_path)
    sf.write(ref_path, y, sr)  # preserved, cleaned reference voice

    pitch, _ = extract_pitch(y, sr)
    energy, _ = extract_energy(y, sr)
    timbre = extract_timbre(y, sr)
    praat = extract_praat(ref_path)
    rhythm = extract_rhythm(y, sr)

    emotion = {"heuristic": heuristic_emotion(pitch, energy, rhythm)}
    if use_emotion:
        emotion["neural"] = neural_emotion(ref_path)

    profile = {
        "metadata": {
            "source_file": os.path.basename(input_path),
            "reference_audio": os.path.basename(ref_path),
            "sample_rate": sr,
            "duration_sec": len(y) / sr,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "tools": {"librosa": librosa.__version__, "parselmouth": HAS_PARSELMOUTH},
        },
        "pitch": pitch,
        "energy_loudness": energy,
        "timbre": timbre,
        "voice_quality_and_formants": praat,
        "rhythm_and_pace": rhythm,
        "emotion_and_tone": emotion,
    }
    if use_embedding:
        profile["speaker_embedding"] = speaker_embedding(ref_path)
    return profile


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else AUDIO_PATH
    output_json = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else OUTPUT_JSON

    if not os.path.isfile(audio_path):
        sys.exit(f"Audio file not found: {audio_path}\nEdit AUDIO_PATH at the top of main.py or run: python main.py <path_to_audio_or_video>")

    base = os.path.splitext(output_json)[0]
    ref_path = base + "_reference.wav"

    print(f"Analyzing: {audio_path} ...")
    profile = build_profile(audio_path, ref_path, USE_EMOTION_MODEL, USE_SPEAKER_EMBEDDING)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(clean(profile), f, indent=2, ensure_ascii=False)

    print(f"Voice profile saved : {output_json}")
    print(f"Reference audio     : {ref_path}")


if __name__ == "__main__":
    main()