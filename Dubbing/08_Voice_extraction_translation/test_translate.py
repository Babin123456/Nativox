#!/usr/bin/env python3
"""
test_translate.py - Translate text and speak it in the author's cloned voice.

Pipeline:
    text --(translate)--> target-language text
         --(XTTS v2, voice embedding built from several clean clips)--> speech,
           sentence by sentence, best of N candidates per sentence
         --(gentle EQ + loudness match from the voice profile)--> final MP3
         --> energy / pitch comparison graph (PNG) + similarity report (JSON)

Run main.py first so these exist:
    voice_profile.json, voice_profile_reference.wav, voice_profile_clips/

Install:
    pip install coqui-tts torch torchaudio deep-translator librosa soundfile scipy matplotlib pydub
    (pydub needs ffmpeg installed on your system for MP3 export)

Usage:
    1. Edit the SETTINGS block below.
    2. Run:  python test_translate.py

Only clone voices you own or have explicit consent to use. Label synthetic
audio as AI-generated when you publish it.
"""

import glob
import json
import os
import re
import sys

# Ensure UTF-8 output on Windows console for Hindi/multilingual text
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np


# Patch torchaudio to use soundfile on Windows (TorchAudio 2.9+ defaults to torchcodec which requires FFmpeg C DLLs)
def _patch_torchaudio_io():
    try:
        import torch
        import torchaudio
        import soundfile as sf

        def _safe_load(uri, frame_offset=0, num_frames=-1, normalize=True, channels_first=True, **kwargs):
            data, sr = sf.read(uri, dtype="float32", start=frame_offset, frames=num_frames if num_frames > 0 else -1)
            tensor = torch.from_numpy(data)
            if tensor.ndim == 1:
                tensor = tensor.unsqueeze(0)
            elif tensor.ndim == 2 and channels_first:
                tensor = tensor.t()
            return tensor, sr

        def _safe_save(uri, src, sample_rate, channels_first=True, **kwargs):
            if isinstance(src, torch.Tensor):
                src = src.detach().cpu().numpy()
            if channels_first and src.ndim > 1:
                src = src.T
            sf.write(uri, src, sample_rate)

        torchaudio.load = _safe_load
        torchaudio.save = _safe_save
    except Exception:
        pass


_patch_torchaudio_io()

import librosa
import soundfile as sf
from scipy import signal
from scipy.ndimage import uniform_filter1d

# =========================================================================== #
# SETTINGS - edit these, then just run:  python test_translate.py
# =========================================================================== #
INPUT_TEXT = "The greatest pleasure I've had is trying to do something that everybody says could not be done."
TARGET_LANG = "hi"                          # e.g. hi, es, fr, de, it, pt, ru, ja, ko, ar, zh-CN, tr, nl, pl, cs, hu
SOURCE_LANG = "auto"                        # "auto" = detect automatically

DEFAULT_OUTPUT_DIR = ".output"
PROFILE_JSON = os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile.json") if os.path.isfile(os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile.json")) else "voice_profile.json"             # created by main.py
REFERENCE_WAV = os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_reference.wav") if os.path.isfile(os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_reference.wav")) else "voice_profile_reference.wav"   # created by main.py
CLIPS_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_clips") if os.path.isdir(os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_clips")) else "voice_profile_clips"               # created by main.py
LATENTS_CACHE = os.path.join(DEFAULT_OUTPUT_DIR, "voice_latents.pt")              # voice embedding cache (auto-created)

OUTPUT_MP3 = os.path.join(DEFAULT_OUTPUT_DIR, "translated_cloned.mp3")
ENERGY_GRAPH_PNG = os.path.join(DEFAULT_OUTPUT_DIR, "energy_graph.png")           # original vs cloned energy + pitch graph
REPORT_JSON = os.path.join(DEFAULT_OUTPUT_DIR, "cloned_audio_report.json")        # similarity numbers

# ---- voice quality (main levers against the "robotic" sound) ---------------
N_CANDIDATES = 2          # generate N takes per sentence, keep the one closest to the original voice
                          # (1 = fastest, 3 = best quality but slower)
TEMPERATURE = 0.70        # higher = more expressive/varied, lower = more stable (0.6 - 0.8)
TOP_K = 50
TOP_P = 0.85
REPETITION_PENALTY = 5.0
LENGTH_PENALTY = 1.0
SPEED = 1.0               # 1.0 = natural; 0.9 slightly slower, 1.1 slightly faster
SEED = 42

# ---- post-processing --------------------------------------------------------
MATCH_TIMBRE_EQ = True    # gently match the tone colour (spectrum) of the original voice
EQ_STRENGTH = 0.5         # 0 - 1
EQ_MAX_DB = 3.0           # never boost/cut more than this
MATCH_LOUDNESS = True     # match average speech loudness of the original
MATCH_PITCH = False       # pitch-shifting adds robotic artifacts; XTTS already clones pitch
PITCH_MAX_SEMITONES = 1.5

SENTENCE_PAUSE_SEC = 0.30
COMMA_PAUSE_SEC = 0.12
# =========================================================================== #

# Languages the XTTS v2 model can speak (Bengali is NOT supported by XTTS)
XTTS_LANGS = {"en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl",
              "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"}

SYNTH_SR = 24000  # XTTS output sample rate


# --------------------------------------------------------------------------- #
# 1. translation
# --------------------------------------------------------------------------- #
def chunk_text(text, limit=4000):
    """Split long text on sentence boundaries so the translator accepts it."""
    sentences = re.split(r"(?<=[.!?।。！？])\s+", text.strip())
    chunks, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) + 1 > limit and cur:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    return chunks


# MyMemory needs region-style codes
MYMEMORY_CODES = {
    "en": "en-GB", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "it": "it-IT",
    "pt": "pt-PT", "pl": "pl-PL", "tr": "tr-TR", "ru": "ru-RU", "nl": "nl-NL",
    "cs": "cs-CZ", "ar": "ar-SA", "zh-cn": "zh-CN", "ja": "ja-JP", "hu": "hu-HU",
    "ko": "ko-KR", "hi": "hi-IN",
}


def _guess_source(text, source):
    """Fallback translators can't auto-detect, so work out the source language."""
    if source and source.lower() != "auto":
        return source.lower()
    try:
        from langdetect import detect
        return detect(text).lower()
    except Exception:
        return "en"


def _google(text, source, target):
    import time
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source=source, target=target)
    out = []
    for chunk in chunk_text(text, 4000):
        for attempt, wait in enumerate((0, 2)):   # fast retry then fallback to MyMemory
            if wait:
                time.sleep(wait)
            try:
                out.append(translator.translate(chunk))
                break
            except Exception as exc:
                if attempt == 1:
                    raise exc
        time.sleep(0.5)
    return " ".join(out)


def _mymemory(text, source, target):
    import time
    from deep_translator import MyMemoryTranslator
    src = MYMEMORY_CODES.get(_guess_source(text, source), _guess_source(text, source))
    tgt = MYMEMORY_CODES.get(target.lower(), target)
    translator = MyMemoryTranslator(source=src, target=tgt)
    out = []
    for chunk in chunk_text(text, 450):                  # MyMemory limit is 500 chars
        out.append(translator.translate(chunk))
        time.sleep(0.3)
    return " ".join(out)


def _argos(text, source, target):
    """Offline translator (downloads a small language pack on first use)."""
    import argostranslate.package as pkg
    import argostranslate.translate as tr
    src = _guess_source(text, source).split("-")[0]
    tgt = target.lower().split("-")[0]
    installed = {l.code for l in tr.get_installed_languages()}
    if not {src, tgt} <= installed:
        pkg.update_package_index()
        for p in pkg.get_available_packages():
            if p.from_code == src and p.to_code == tgt:
                pkg.install_from_path(p.download())
                break
    return tr.translate(text, src, tgt)


def translate(text, source, target):
    try:
        import deep_translator  # noqa: F401
    except ImportError:
        sys.exit("Missing package. Run: pip install deep-translator")

    engines = [("Google", _google), ("MyMemory", _mymemory), ("Argos (offline)", _argos)]
    errors = []
    for name, fn in engines:
        try:
            print(f"Translating with {name} ...")
            result = fn(text, source, target)
            if result and result.strip():
                return result
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            print(f"  {name} failed, trying next engine ...")
    sys.exit("All translation engines failed:\n  " + "\n  ".join(errors) +
             "\nWait a few minutes, check your internet, or run: pip install argostranslate langdetect")


# --------------------------------------------------------------------------- #
# audio helpers
# --------------------------------------------------------------------------- #
def active_db_mean(y):
    """Mean loudness (dB) over active (speech) frames only, ignoring pauses."""
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
    active = db[db > np.percentile(db, 95) - 25]
    return float(np.mean(active)) if active.size else float(np.mean(db))


def highpass(y, sr, cutoff=60):
    sos = signal.butter(4, cutoff, btype="highpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y).astype(np.float32)


def tidy_chunk(w, sr=SYNTH_SR):
    """Trim the silence/noise XTTS leaves around a sentence and fade the edges."""
    w = np.asarray(w, dtype=np.float32).squeeze()
    if w.size == 0:
        return w
    w, _ = librosa.effects.trim(w, top_db=35)
    n = int(sr * 0.012)
    if w.size > 2 * n:
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        w = w.copy()
        w[:n] *= ramp
        w[-n:] *= ramp[::-1]
    return w


# --------------------------------------------------------------------------- #
# 2. voice cloning (XTTS v2) - voice embedding + sentence-wise generation
# --------------------------------------------------------------------------- #
def load_model():
    os.environ.setdefault("COQUI_TOS_AGREED", "1")  # accepts the XTTS licence prompt
    try:
        import torch
    except ImportError:
        sys.exit("PyTorch is not installed. Run:\n    pip install torch torchaudio")
    try:
        from TTS.api import TTS
    except ImportError as exc:
        sys.exit(f"Failed to load Coqui TTS: {exc}\nEnsure torch and coqui-tts are installed.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading XTTS v2 on {device} (first run downloads ~2 GB) ...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return tts.synthesizer.tts_model, device, torch


def get_voice_embedding(model, device, torch):
    """Build the speaker embedding + GPT conditioning from ALL clean clips (cached)."""
    clips = sorted(glob.glob(os.path.join(CLIPS_DIR, "*.wav")))
    sources = clips if clips else [REFERENCE_WAV]
    newest = max(os.path.getmtime(p) for p in sources + [REFERENCE_WAV])

    if os.path.isfile(LATENTS_CACHE) and os.path.getmtime(LATENTS_CACHE) > newest:
        try:
            d = torch.load(LATENTS_CACHE, map_location=device)
            print("Using cached voice embedding.")
            return d["gpt"].to(device), d["spk"].to(device)
        except Exception:
            pass

    print(f"Computing voice embedding from {len(sources)} clean clip(s) ...")
    try:
        gpt, spk = model.get_conditioning_latents(
            audio_path=sources, gpt_cond_len=30, gpt_cond_chunk_len=6, max_ref_length=60)
    except TypeError:
        gpt, spk = model.get_conditioning_latents(audio_path=sources)
    torch.save({"gpt": gpt.detach().cpu(), "spk": spk.detach().cpu()}, LATENTS_CACHE)
    return gpt, spk


def _wrap(s, max_len):
    words, out, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_len and cur:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def split_text(text, max_len=200):
    """Sentence-wise chunks (XTTS sounds best on short, complete sentences)."""
    chunks = []
    for p in re.split(r"(?<=[.!?।。！？])\s+", text.strip()):
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_len:
            chunks.append((p, SENTENCE_PAUSE_SEC))
            continue
        cur = ""
        for pc in re.split(r"(?<=[,;:，、])\s+", p):
            if len(cur) + len(pc) + 1 > max_len and cur:
                chunks.append((cur, COMMA_PAUSE_SEC))
                cur = pc
            else:
                cur = f"{cur} {pc}".strip()
        for piece in _wrap(cur, max_len):
            chunks.append((piece, COMMA_PAUSE_SEC))
        chunks[-1] = (chunks[-1][0], SENTENCE_PAUSE_SEC)
    return chunks


def synth_chunk(model, torch, text, lang, gpt, spk, seed):
    torch.manual_seed(seed)
    kwargs = dict(text=text, language=lang, gpt_cond_latent=gpt, speaker_embedding=spk)
    try:
        out = model.inference(**kwargs, temperature=TEMPERATURE, length_penalty=LENGTH_PENALTY,
                              repetition_penalty=REPETITION_PENALTY, top_k=TOP_K, top_p=TOP_P,
                              speed=SPEED, enable_text_splitting=False)
    except TypeError:
        out = model.inference(**kwargs)
    return tidy_chunk(np.asarray(out["wav"], dtype=np.float32))


def reference_stats(profile):
    pitch = profile.get("pitch", {})
    mfcc = profile.get("timbre", {}).get("mfcc_mean")
    return {
        "f0_med": pitch.get("f0_hz_median"),
        "f0_std": pitch.get("intonation_variability_semitone_std"),
        "mfcc": np.array(mfcc, dtype=float) if mfcc else None,
    }


def score_candidate(w, ref):
    """Lower = closer to the original voice (timbre, pitch level, expressiveness)."""
    y = librosa.resample(w, orig_sr=SYNTH_SR, target_sr=22050)
    score = 0.0
    if ref["mfcc"] is not None:
        mf = np.mean(librosa.feature.mfcc(y=y, sr=22050, n_mfcc=20), axis=1)
        score += 0.15 * float(np.linalg.norm(mf[1:13] - ref["mfcc"][1:13]))
    f0, _, _ = librosa.pyin(y, fmin=65, fmax=500, sr=22050, frame_length=2048, hop_length=256)
    v = f0[~np.isnan(f0)]
    if v.size >= 10 and ref["f0_med"]:
        med = np.median(v)
        score += abs(12 * np.log2(med / ref["f0_med"]))
        if ref["f0_std"] is not None:                      # flat pitch = robotic
            score += 1.5 * abs(float(np.std(12 * np.log2(v / med))) - ref["f0_std"])
    return score


def generate_speech(model, torch, text, lang, gpt, spk, ref):
    chunks = split_text(text)
    pieces = []
    for i, (txt, pause) in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {txt[:70]}")
        cands = []
        for k in range(max(1, N_CANDIDATES)):
            w = synth_chunk(model, torch, txt, lang, gpt, spk, SEED + k * 101)
            if w.size > int(0.2 * SYNTH_SR):
                cands.append(w)
        if not cands:
            continue
        best = cands[0] if len(cands) == 1 else min(cands, key=lambda c: score_candidate(c, ref))
        pieces += [best, np.zeros(int(pause * SYNTH_SR), dtype=np.float32)]
    if not pieces:
        sys.exit("XTTS produced no audio. Try a different sentence or check the reference clips.")
    return np.concatenate(pieces[:-1])


# --------------------------------------------------------------------------- #
# 3. post-processing from the extracted voice features
# --------------------------------------------------------------------------- #
def load_profile(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _avg_spectrum(y, n_fft=2048, hop=512):
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    db = librosa.amplitude_to_db(librosa.feature.rms(S=S, frame_length=n_fft, hop_length=hop)[0] + 1e-9)
    active = db > np.percentile(db, 95) - 25
    return np.mean(S[:, active], axis=1) if active.any() else np.mean(S, axis=1)


def match_timbre_eq(y, sr, ref_y):
    """Gentle smooth EQ so the long-term spectrum matches the original voice."""
    n_fft, hop = 2048, 512
    diff_db = 20 * np.log10((_avg_spectrum(ref_y) + 1e-8) / (_avg_spectrum(y) + 1e-8))
    diff_db = uniform_filter1d(diff_db, size=33, mode="nearest")
    freqs = np.linspace(0, sr / 2, diff_db.size)
    band = np.clip((freqs - 80) / 200, 0, 1) * np.clip((7500 - freqs) / 500, 0, 1)
    gain_db = np.clip(diff_db * EQ_STRENGTH, -EQ_MAX_DB, EQ_MAX_DB) * band
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    out = librosa.istft(S * (10 ** (gain_db / 20))[:, None], hop_length=hop, length=len(y))
    return out.astype(np.float32), float(np.max(np.abs(gain_db)))


def match_loudness(y, target_db):
    gain_db = float(np.clip(target_db - active_db_mean(y), -8.0, 8.0))
    return (y * (10 ** (gain_db / 20))).astype(np.float32), gain_db


def match_pitch(y, sr, target_f0):
    f0, _, _ = librosa.pyin(y, fmin=65, fmax=500, sr=sr, frame_length=2048, hop_length=256)
    f0 = f0[~np.isnan(f0)]
    if f0.size == 0 or not target_f0:
        return y, 0.0
    steps = float(np.clip(12 * np.log2(target_f0 / np.median(f0)), -PITCH_MAX_SEMITONES, PITCH_MAX_SEMITONES))
    if abs(steps) < 1.0:
        return y, 0.0
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=steps), steps


def postprocess(y, profile, ref_y):
    report = {}
    y = highpass(y, SYNTH_SR)
    y = (y / (np.max(np.abs(y)) or 1.0) * 0.95).astype(np.float32)

    if MATCH_TIMBRE_EQ:
        y, max_db = match_timbre_eq(y, SYNTH_SR, ref_y)
        report["timbre_eq_max_change_db"] = round(max_db, 2)

    if MATCH_PITCH:
        y, steps = match_pitch(y, SYNTH_SR, profile.get("pitch", {}).get("f0_hz_median"))
        report["pitch_shift_semitones"] = round(steps, 2)

    if MATCH_LOUDNESS:
        el = profile.get("energy_loudness", {})
        target = el.get("speech_loudness_db_mean", el.get("loudness_db_mean"))
        if target is not None:
            y, gain = match_loudness(y, target)
            report["loudness_gain_db"] = round(gain, 2)

    peak = np.max(np.abs(y)) or 1.0
    if peak > 0.98:                                       # avoid clipping
        y = y / peak * 0.98
    return y.astype(np.float32), report


# --------------------------------------------------------------------------- #
# 4. analysis, energy graph, similarity report
# --------------------------------------------------------------------------- #
def analyze(y, sr):
    y22 = librosa.resample(y, orig_sr=sr, target_sr=22050) if sr != 22050 else y
    hop = 256
    rms = librosa.feature.rms(y=y22, frame_length=2048, hop_length=hop)[0]
    db = np.maximum(librosa.amplitude_to_db(rms + 1e-9), -80.0)
    f0, _, _ = librosa.pyin(y22, fmin=65, fmax=500, sr=22050, frame_length=2048, hop_length=hop)
    v = f0[~np.isnan(f0)]
    cent = librosa.feature.spectral_centroid(y=y22, sr=22050)[0]
    metrics = {
        "duration_sec": len(y) / sr,
        "speech_loudness_db": active_db_mean(y22),
        "dynamic_range_db": float(np.percentile(db, 95) - np.percentile(db, 5)),
        "f0_median_hz": float(np.median(v)) if v.size else None,
        "intonation_std_semitones": float(np.std(12 * np.log2(v / np.median(v)))) if v.size else None,
        "spectral_centroid_hz": float(np.mean(cent)),
    }
    contours = {
        "t": librosa.times_like(rms, sr=22050, hop_length=hop), "db": db,
        "tf": librosa.times_like(f0, sr=22050, hop_length=hop), "f0": f0,
    }
    return metrics, contours


def save_energy_graph(ref_m, ref_c, gen_m, gen_c, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    blue, red = "#4C72B0", "#C44E52"
    fig, ax = plt.subplots(4, 1, figsize=(13, 13))

    for a, c, m, color, name in ((ax[0], ref_c, ref_m, blue, "ORIGINAL voice (reference)"),
                                 (ax[1], gen_c, gen_m, red, "CLONED translated voice")):
        sm = uniform_filter1d(c["db"], 7)
        a.fill_between(c["t"], -80, sm, color=color, alpha=0.25)
        a.plot(c["t"], c["db"], color="#B0B0B0", lw=0.7)
        a.plot(c["t"], sm, color=color, lw=1.6)
        a.axhline(m["speech_loudness_db"], ls="--", color="black", lw=0.9)
        a.set_title(f"{name} - energy over time (mean speech {m['speech_loudness_db']:.1f} dB)", fontsize=11)
        a.set_ylabel("Energy (dB)")
        a.set_xlabel("Time (s)")
        a.set_ylim(-80, 0)

    grid = np.linspace(0, 100, 500)
    for c, color, label in ((ref_c, blue, "original"), (gen_c, red, "cloned")):
        ax[2].plot(grid, np.interp(grid, c["t"] / c["t"][-1] * 100, uniform_filter1d(c["db"], 9)),
                   color=color, lw=1.8, label=label)
        ax[3].plot(c["tf"] / c["tf"][-1] * 100, c["f0"], ".", ms=2.5, color=color, alpha=0.6, label=label)
    ax[2].set_title("Energy overlay (time normalised to 0-100%, so different lengths can be compared)", fontsize=11)
    ax[2].set_ylabel("Energy (dB)")
    ax[2].set_ylim(-80, 0)
    ax[3].set_title("Pitch (F0) overlay - a flat line means robotic delivery", fontsize=11)
    ax[3].set_ylabel("F0 (Hz)")
    ax[3].set_xlabel("Progress (%)")
    for a in ax:
        a.grid(alpha=0.25)
    ax[2].legend()
    ax[3].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_report(ref_m, gen_m, adjustments):
    def diff(k):
        a, b = ref_m.get(k), gen_m.get(k)
        return None if a is None or b is None else round(b - a, 3)

    f0_semi = None
    if ref_m["f0_median_hz"] and gen_m["f0_median_hz"]:
        f0_semi = round(12 * float(np.log2(gen_m["f0_median_hz"] / ref_m["f0_median_hz"])), 2)
    return {
        "original": ref_m,
        "cloned": gen_m,
        "differences_cloned_minus_original": {
            "f0_median_semitones": f0_semi,
            "speech_loudness_db": diff("speech_loudness_db"),
            "intonation_std_semitones": diff("intonation_std_semitones"),
            "spectral_centroid_hz": diff("spectral_centroid_hz"),
        },
        "postprocessing_applied": adjustments,
    }


# --------------------------------------------------------------------------- #
# 5. export mp3
# --------------------------------------------------------------------------- #
def save_mp3(y, sr, mp3_path):
    wav_path = os.path.splitext(mp3_path)[0] + ".wav"
    sf.write(wav_path, y, sr)
    try:
        from pydub import AudioSegment
        AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3", bitrate="192k")
    except Exception:
        try:
            sf.write(mp3_path, y, sr, format="MP3")   # needs libsndfile >= 1.1
        except Exception as exc:
            print(f"MP3 export failed ({exc}). Install ffmpeg + pydub. WAV kept at: {wav_path}")
            return wav_path
    return mp3_path


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    for p in (PROFILE_JSON, REFERENCE_WAV):
        if not os.path.isfile(p):
            sys.exit(f"Missing file: {p}\nRun 'python main.py' first to create it.")

    lang = TARGET_LANG.lower()
    if lang == "zh":
        lang = "zh-cn"
    if lang not in XTTS_LANGS:
        sys.exit(f"XTTS cannot speak '{TARGET_LANG}'. Supported: {sorted(XTTS_LANGS)}")

    profile = load_profile(PROFILE_JSON)

    translated = translate(INPUT_TEXT, SOURCE_LANG, TARGET_LANG)
    print(f"Translated text: {translated}\n")

    model, device, torch = load_model()
    gpt, spk = get_voice_embedding(model, device, torch)
    ref_y, _ = librosa.load(REFERENCE_WAV, sr=SYNTH_SR, mono=True)

    print(f"Generating speech ({N_CANDIDATES} candidate(s) per sentence) ...")
    y = generate_speech(model, torch, translated, lang, gpt, spk, reference_stats(profile))

    print("Matching voice features from profile ...")
    y, adjustments = postprocess(y, profile, ref_y)
    out = save_mp3(y, SYNTH_SR, OUTPUT_MP3)

    print("Analysing original vs cloned voice ...")
    ref_m, ref_c = analyze(ref_y, SYNTH_SR)
    gen_m, gen_c = analyze(y, SYNTH_SR)
    save_energy_graph(ref_m, ref_c, gen_m, gen_c, ENERGY_GRAPH_PNG)
    report = build_report(ref_m, gen_m, adjustments)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    d = report["differences_cloned_minus_original"]
    print(f"\nAdjustments applied : {adjustments}")
    print(f"Pitch difference    : {d['f0_median_semitones']} semitones (0 = identical)")
    print(f"Loudness difference : {d['speech_loudness_db']} dB (0 = identical)")
    print(f"Cloned audio        : {out}")
    print(f"Energy graph        : {ENERGY_GRAPH_PNG}")
    print(f"Similarity report   : {REPORT_JSON}")


if __name__ == "__main__":
    main()