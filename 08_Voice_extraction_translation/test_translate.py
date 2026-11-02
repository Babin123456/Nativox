#!/usr/bin/env python3
"""
test_translate.py - Translate text and speak it in the author's cloned voice.

Pipeline:
    text  --(translate)-->  target-language text
          --(XTTS v2 voice cloning using voice_profile_reference.wav)-->  speech
          --(match pitch + loudness from voice_profile.json)-->  final MP3

Run main.py first so these two files exist:
    voice_profile.json
    voice_profile_reference.wav

Install:
    pip install coqui-tts deep-translator librosa soundfile numpy pydub
    (pydub needs ffmpeg installed on your system for MP3 export)

Usage:
    1. Edit the SETTINGS block below.
    2. Run:  python test_translate.py

Only clone voices you own or have explicit consent to use. Label synthetic
audio as AI-generated when you publish it.
"""

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

# =========================================================================== #
# SETTINGS - edit these, then just run:  python test_translate.py
# =========================================================================== #
INPUT_TEXT = "The greatest pleasure I've had is trying to do something that everybody says could not be done."
TARGET_LANG = "hi"                          # e.g. hi, es, fr, de, it, pt, ru, ja, ko, ar, zh-CN, tr, nl, pl, cs, hu
SOURCE_LANG = "auto"                        # "auto" = detect automatically

PROFILE_JSON = "voice_profile.json"         # created by main.py
REFERENCE_WAV = "voice_profile_reference.wav"  # created by main.py
OUTPUT_MP3 = "translated_cloned.mp3"

MATCH_PITCH = True       # shift generated pitch toward the author's median F0 (from the JSON)
MATCH_LOUDNESS = True    # match the author's average loudness (from the JSON)
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
# 2. voice cloning (XTTS v2)
# --------------------------------------------------------------------------- #
def synthesize(text, lang, reference_wav, out_wav):
    os.environ.setdefault("COQUI_TOS_AGREED", "1")  # accepts the XTTS licence prompt
    try:
        import torch
        from TTS.api import TTS
    except ImportError as exc:
        sys.exit(f"Failed to load Coqui TTS: {exc}\nEnsure torch, torchcodec, and coqui-tts are installed.")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading XTTS v2 on {device} (first run downloads ~2 GB) ...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_wav,   # the preserved original voice
        language=lang,
        file_path=out_wav,
        split_sentences=True,
    )


# --------------------------------------------------------------------------- #
# 3. apply extracted voice features from the JSON
# --------------------------------------------------------------------------- #
def load_profile(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_pitch(y, sr, target_f0):
    import librosa
    f0, _, _ = librosa.pyin(y, fmin=65, fmax=500, sr=sr, frame_length=2048, hop_length=256)
    f0 = f0[~np.isnan(f0)]
    if f0.size == 0 or not target_f0:
        return y, 0.0
    steps = 12 * np.log2(target_f0 / np.median(f0))
    steps = float(np.clip(steps, -4.0, 4.0))          # keep the correction gentle
    if abs(steps) < 0.5:                              # already close enough
        return y, 0.0
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=steps), steps


def match_loudness(y, target_db):
    import librosa
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    cur_db = float(np.mean(librosa.amplitude_to_db(rms + 1e-9)))
    gain_db = float(np.clip(target_db - cur_db, -12.0, 12.0))
    y = y * (10 ** (gain_db / 20))
    peak = np.max(np.abs(y)) or 1.0
    if peak > 0.98:                                   # avoid clipping
        y = y / peak * 0.98
    return y, gain_db


def postprocess(wav_path, profile):
    import librosa
    y, sr = librosa.load(wav_path, sr=SYNTH_SR, mono=True)
    y = (y / (np.max(np.abs(y)) or 1.0) * 0.95).astype(np.float32)
    report = {}

    if MATCH_PITCH:
        target_f0 = profile.get("pitch", {}).get("f0_hz_median")
        y, steps = match_pitch(y, sr, target_f0)
        report["pitch_shift_semitones"] = round(steps, 2)

    if MATCH_LOUDNESS:
        target_db = profile.get("energy_loudness", {}).get("loudness_db_mean")
        if target_db is not None:
            y, gain = match_loudness(y, target_db)
            report["loudness_gain_db"] = round(gain, 2)

    return y, sr, report


# --------------------------------------------------------------------------- #
# 4. export mp3
# --------------------------------------------------------------------------- #
def save_mp3(y, sr, mp3_path):
    import soundfile as sf
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

    raw_wav = "_raw_synth.wav"
    synthesize(translated, lang, REFERENCE_WAV, raw_wav)

    print("Matching voice features from profile ...")
    y, sr, report = postprocess(raw_wav, profile)
    out = save_mp3(y, sr, OUTPUT_MP3)

    if os.path.exists(raw_wav):
        os.remove(raw_wav)

    print(f"\nAdjustments applied: {report}")
    print(f"Done. Cloned translated audio saved to: {out}")


if __name__ == "__main__":
    main()