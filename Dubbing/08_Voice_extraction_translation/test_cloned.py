#!/usr/bin/env python3
"""
test_cloned.py - Speak any text in the author's cloned voice.
==============================================================

Pipeline:
    text --> auto-detect language (script based) --> clean / normalise text
         --> XTTS v2 (voice cloned from the clean reference clips)
         --> duration matching (output ~ same length as the original recording)
         --> gentle EQ + loudness match (voice only)
         --> original BACKGROUND sound mixed back in, untouched
         --> WAV + MP3 (+ energy graph PNG)

Run main.py first so these exist:
    voice_profile.json, voice_profile_reference.wav, voice_profile_clips/,
    voice_profile_background.wav (the original background, saved by main.py)

Background: added to the cloned voice with no EQ, no gain change and no pitch/tempo
change. Pass --no-background to skip it.

Install:
    pip install coqui-tts torch torchaudio librosa soundfile scipy matplotlib pydub
    pip install langdetect num2words      # optional: Latin-script language detection / numbers
    (pydub needs ffmpeg on your system for MP3 export)

Usage:
    1. Set INPUT_TEXT below (LANGUAGE can stay "auto").
    2. Run:  python test_cloned.py

Only clone voices you own or have explicit consent to use.
Label synthetic audio as AI-generated when you publish it.
"""

import glob
import json
import os
import re
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np


# Patch torchaudio to use soundfile on Windows
# (TorchAudio 2.9+ defaults to torchcodec which requires FFmpeg C DLLs)
def _patch_torchaudio_io():
    try:
        import torch
        import torchaudio
        import soundfile as sf

        def _safe_load(uri, frame_offset=0, num_frames=-1,
                       normalize=True, channels_first=True, **kwargs):
            data, sr = sf.read(uri, dtype="float32",
                               start=frame_offset,
                               frames=num_frames if num_frames > 0 else -1)
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
# SETTINGS - edit these, then run:  python test_cloned.py
# =========================================================================== #

# The text to speak in the cloned voice (it will be auto-detected)
INPUT_TEXT = "मेरे लिए सबसे बड़ी खुशी कुछ ऐसा करने का प्रयास करना है जिसके बारे में हर कोई कहता है कि यह नहीं किया जा सकता।"

# "auto" = detect from the text. Or force: hi, en, es, fr, de, it, pt, pl,
# tr, ru, nl, cs, ar, zh-cn, ja, hu, ko.  (A wrong code makes XTTS sound like a
# mixture of two languages - e.g. Hindi text with "en".)
LANGUAGE = "auto"

# Voice profile files (created by main.py)
DEFAULT_OUTPUT_DIR = ".output"
OUTPUT_MP3 = os.path.join(DEFAULT_OUTPUT_DIR, "cloned_output.mp3")
OUTPUT_WAV = os.path.join(DEFAULT_OUTPUT_DIR, "cloned_output.wav")
ENERGY_GRAPH_PNG = os.path.join(DEFAULT_OUTPUT_DIR, "cloned_energy_graph.png")     # original vs cloned energy + pitch
SAVE_ENERGY_GRAPH = True

# ---- Background sound (kept exactly as in the original recording) ------------
PRESERVE_BACKGROUND = True
OUTPUT_VOICE_ONLY_WAV = os.path.join(DEFAULT_OUTPUT_DIR, "cloned_voice_only.wav")   # cloned voice without background (for checking)
# If the cloned voice is longer than the original recording, the background is
# "loop"ed (first pass untouched, 20 ms fade-in on repeats) or continued as "silence".
BACKGROUND_FIT = "loop"

PROFILE_JSON = os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile.json") if os.path.isfile(os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile.json")) else "voice_profile.json"
REFERENCE_WAV = os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_reference.wav") if os.path.isfile(os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_reference.wav")) else "voice_profile_reference.wav"
CLIPS_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_clips") if os.path.isdir(os.path.join(DEFAULT_OUTPUT_DIR, "voice_profile_clips")) else "voice_profile_clips"
LATENTS_CACHE = os.path.join(DEFAULT_OUTPUT_DIR, "voice_latents.pt")              # auto-created; speeds up re-runs


# ---- Length control ---------------------------------------------------------
MATCH_ORIGINAL_DURATION = True   # make the output about as long as the original recording
TARGET_DURATION_SEC = None       # or set a number (e.g. 8.0) to force a target length
DURATION_TOLERANCE = 0.10        # accept +-10 % without re-generating
MIN_SPEED, MAX_SPEED = 0.85, 1.30  # speech-rate limits (beyond this it sounds unnatural)

# ---- Voice quality knobs ----------------------------------------------------
N_CANDIDATES = 2          # takes per sentence; the one closest to the original voice wins
TEMPERATURE = 0.65        # higher = more expressive, lower = more stable (0.6 - 0.8)
TOP_K = 50
TOP_P = 0.85
REPETITION_PENALTY = 5.0
LENGTH_PENALTY = 1.0
SPEED = 1.0               # starting speech rate (auto-adjusted by length control)
SEED = 42

# ---- Post-processing --------------------------------------------------------
MATCH_TIMBRE_EQ = True
EQ_STRENGTH = 0.5
EQ_MAX_DB = 3.0
MATCH_LOUDNESS = True

SENTENCE_PAUSE_SEC = 0.25
COMMA_PAUSE_SEC = 0.10
# =========================================================================== #

XTTS_LANGS = {"en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
              "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"}

SYNTH_SR = 24000  # XTTS v2 output sample rate


# --------------------------------------------------------------------------- #
# language detection + text clean-up
# --------------------------------------------------------------------------- #
def detect_language(text):
    """Detect the language from the writing script (reliable for Hindi etc.)."""
    counts = {}
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            k = "hi"                       # Devanagari
        elif 0x0980 <= o <= 0x09FF:
            k = "bn"                       # Bengali (not supported by XTTS)
        elif 0x0A00 <= o <= 0x0DFF:
            k = "other-indic"              # Gurmukhi ... Malayalam (not supported)
        elif 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F:
            k = "ar"
        elif 0x3040 <= o <= 0x30FF:
            k = "ja"
        elif 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF:
            k = "ko"
        elif 0x4E00 <= o <= 0x9FFF:
            k = "zh-cn"
        elif 0x0400 <= o <= 0x04FF:
            k = "ru"
        elif ch.isalpha():
            k = "latin"
        else:
            continue
        counts[k] = counts.get(k, 0) + 1

    if not counts:
        return "en"
    if "ja" in counts:                     # kana present -> Japanese (kanji are shared with Chinese)
        return "ja"
    dominant = max(counts, key=counts.get)
    if dominant != "latin":
        return dominant

    try:                                   # Latin script: English, Spanish, French ...
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        code = detect(text).lower()
        code = "zh-cn" if code.startswith("zh") else code
        return code if code in XTTS_LANGS else "en"
    except Exception:
        return "en"


def resolve_language(text, setting):
    detected = detect_language(text)
    s = (setting or "auto").strip().lower()
    s = "zh-cn" if s == "zh" else s

    if detected in ("bn", "other-indic"):
        sys.exit("XTTS v2 cannot speak this script (e.g. Bengali). Use a supported language "
                 f"such as Hindi (hi).\nSupported: {sorted(XTTS_LANGS)}")
    if s == "auto":
        return detected
    if s not in XTTS_LANGS:
        sys.exit(f"XTTS v2 cannot speak '{setting}'.\nSupported: {sorted(XTTS_LANGS)}")
    if detected != s and detected in XTTS_LANGS and detected != "en" and s != detected:
        # the text is written in a non-Latin script that contradicts the chosen code
        print(f"WARNING: text looks like '{detected}' but LANGUAGE='{setting}'. "
              f"Using '{detected}' to avoid a mixed-accent voice.")
        return detected
    return s


def normalize_text(text, lang):
    """Clean text so XTTS reads it fluently in one language."""
    text = text.strip()
    text = text.replace("…", ".").replace("—", ", ").replace("–", ", ")
    text = re.sub(r"[\"“”‘’«»()\[\]{}*_#~^|\\<>]", " ", text)
    text = re.sub(r"\s+", " ", text)

    try:                                    # digits -> words in the target language
        from num2words import num2words
        code = "zh" if lang == "zh-cn" else lang

        def _num(m):
            try:
                return num2words(int(m.group()), lang=code)
            except Exception:
                return m.group()
        text = re.sub(r"\d+", _num, text)
    except ImportError:
        pass

    latin_words = re.findall(r"[A-Za-z]{2,}", text)
    if latin_words and lang in ("hi", "ar", "ru", "ja", "ko", "zh-cn"):
        print(f"NOTE: text contains Latin words {latin_words[:6]}. XTTS reads them with a "
              f"{lang} accent, which sounds mixed. Write them in the native script for best results.")
    return text.strip()


# --------------------------------------------------------------------------- #
# audio helpers
# --------------------------------------------------------------------------- #
def active_db_mean(y):
    """Mean loudness (dB) over active (speech) frames, ignoring silences."""
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
    active = db[db > np.percentile(db, 95) - 25]
    return float(np.mean(active)) if active.size else float(np.mean(db))


def highpass(y, sr, cutoff=60):
    sos = signal.butter(4, cutoff, btype="highpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y).astype(np.float32)


def tidy_chunk(w, sr=SYNTH_SR):
    """Trim silence/noise XTTS leaves around a sentence and fade edges, preserving speech tail."""
    w = np.asarray(w, dtype=np.float32).squeeze()
    if w.size == 0:
        return w
    # Use conservative 48 dB threshold to avoid clipping soft ending consonants
    w, _ = librosa.effects.trim(w, top_db=48)
    # Add 120ms safety padding at the tail so the final word isn't abruptly cut
    tail_pad = int(sr * 0.12)
    w = np.pad(w, (0, tail_pad))
    n = int(sr * 0.012)
    if w.size > 2 * n:
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        w = w.copy()
        w[:n] *= ramp
        w[-n:] *= ramp[::-1]
    return w


# --------------------------------------------------------------------------- #
# XTTS v2 - model loading + voice embedding
# --------------------------------------------------------------------------- #
def load_model():
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    try:
        import torch
    except ImportError:
        sys.exit("PyTorch is not installed. Run:\n    pip install torch torchaudio")
    try:
        from TTS.api import TTS
    except ImportError as exc:
        sys.exit(f"Failed to load Coqui TTS: {exc}\nRun: pip install coqui-tts")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading XTTS v2 on {device} (first run downloads ~2 GB) ...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return tts.synthesizer.tts_model, device, torch


def get_voice_embedding(model, device, torch, clips_dir=None, ref_wav=None, cache_path=None):
    """Build speaker embedding + GPT conditioning from all clean clips (cached)."""
    c_dir = clips_dir or CLIPS_DIR
    r_wav = ref_wav or REFERENCE_WAV
    c_cache = cache_path or LATENTS_CACHE

    clips = sorted(glob.glob(os.path.join(c_dir, "*.wav")))
    sources = clips if clips else ([r_wav] if os.path.isfile(r_wav) else [])
    if not sources:
        raise FileNotFoundError(f"No reference audio found at {r_wav} or clips in {c_dir}")

    newest = max(os.path.getmtime(p) for p in sources)

    if os.path.isfile(c_cache) and os.path.getmtime(c_cache) > newest:
        try:
            d = torch.load(c_cache, map_location=device)
            print("Using cached voice embedding.")
            return d["gpt"].to(device), d["spk"].to(device)
        except Exception:
            pass

    print(f"Computing voice embedding from {len(sources)} clean clip(s) ...")
    try:
        gpt, spk = model.get_conditioning_latents(
            audio_path=sources, gpt_cond_len=30,
            gpt_cond_chunk_len=6, max_ref_length=60,
        )
    except TypeError:
        gpt, spk = model.get_conditioning_latents(audio_path=sources)
    try:
        torch.save({"gpt": gpt.detach().cpu(), "spk": spk.detach().cpu()}, c_cache)
    except Exception:
        pass
    return gpt, spk


# --------------------------------------------------------------------------- #
# text splitting + sentence-wise synthesis
# --------------------------------------------------------------------------- #
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


def split_text(text, lang, max_len=95):
    """Sentence-wise chunks; splits clauses naturally so XTTS never cuts off trailing words."""
    end_mark = "।" if lang == "hi" else "。" if lang in ("ja", "zh-cn") else "."
    chunks = []
    # Also split on natural conjunctions / pauses like 'जिसके', 'कि', commas, etc.
    for p in re.split(r"(?<=[.!?।。！？])\s+", text.strip()):
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_len:
            pieces = [(p, SENTENCE_PAUSE_SEC)]
        else:
            pieces, cur = [], ""
            # Split by comma or subordinating conjunctions if clause is long
            split_regex = r"(?<=[,;:，、])\s+|(?<=\s)(?=जिसके|ताकि|क्योंकि|लेकिन|किन्तु|परन्तु|परंतु|कि\s)" if lang == "hi" else r"(?<=[,;:，、])\s+"
            for pc in re.split(split_regex, p):
                if not pc:
                    continue
                if len(cur) + len(pc) + 1 > max_len and cur:
                    pieces.append((cur, COMMA_PAUSE_SEC))
                    cur = pc
                else:
                    cur = f"{cur} {pc}".strip()
            if cur:
                pieces += [(w, COMMA_PAUSE_SEC) for w in _wrap(cur, max_len)]
            if pieces:
                pieces[-1] = (pieces[-1][0], SENTENCE_PAUSE_SEC)
        if not pieces:
            continue
        # a missing full stop makes XTTS ramble / add extra sound at the end
        txt, pause = pieces[-1]
        if not re.search(r"[.!?।。！？]$", txt):
            pieces[-1] = (txt + end_mark, pause)
        chunks += pieces
    return chunks


def reference_stats(profile):
    pitch = profile.get("pitch", {})
    mfcc = profile.get("timbre", {}).get("mfcc_mean")
    return {
        "f0_med": pitch.get("f0_hz_median"),
        "f0_std": pitch.get("intonation_variability_semitone_std"),
        "mfcc": np.array(mfcc, dtype=float) if mfcc else None,
    }


def score_candidate(w, ref):
    """Lower = closer to original voice (timbre + pitch level + expressiveness)."""
    y = librosa.resample(w, orig_sr=SYNTH_SR, target_sr=22050)
    score = 0.0
    if ref["mfcc"] is not None:
        mf = np.mean(librosa.feature.mfcc(y=y, sr=22050, n_mfcc=20), axis=1)
        score += 0.15 * float(np.linalg.norm(mf[1:13] - ref["mfcc"][1:13]))
    f0, _, _ = librosa.pyin(y, fmin=65, fmax=500, sr=22050,
                            frame_length=2048, hop_length=256)
    v = f0[~np.isnan(f0)]
    if v.size >= 10 and ref["f0_med"]:
        med = np.median(v)
        score += abs(12 * np.log2(med / ref["f0_med"]))
        if ref["f0_std"] is not None:
            score += 1.5 * abs(float(np.std(12 * np.log2(v / med))) - ref["f0_std"])
    return score


def synth_chunk(model, torch, text, lang, gpt, spk, seed, speed):
    torch.manual_seed(seed)
    kwargs = dict(text=text, language=lang,
                  gpt_cond_latent=gpt, speaker_embedding=spk)
    try:
        out = model.inference(
            **kwargs,
            temperature=TEMPERATURE, length_penalty=LENGTH_PENALTY,
            repetition_penalty=REPETITION_PENALTY,
            top_k=TOP_K, top_p=TOP_P,
            speed=speed, enable_text_splitting=False,
        )
    except TypeError:
        out = model.inference(**kwargs)
    return tidy_chunk(np.asarray(out["wav"], dtype=np.float32))


def generate_speech(model, torch, text, lang, gpt, spk, ref, speed):
    """Generate speech sentence-by-sentence, keeping the best candidate each time."""
    chunks = split_text(text, lang)
    pieces = []
    for i, (txt, pause) in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {txt[:80]}")
        cands = []
        for k in range(max(1, N_CANDIDATES)):
            w = synth_chunk(model, torch, txt, lang, gpt, spk, SEED + k * 101, speed)
            if w.size > int(0.2 * SYNTH_SR):
                cands.append(w)
        if not cands:
            continue
        best = cands[0] if len(cands) == 1 else min(cands, key=lambda c: score_candidate(c, ref))
        gap = np.zeros(int(pause / max(speed, 0.5) * SYNTH_SR), dtype=np.float32)
        pieces += [best, gap]
    if not pieces:
        sys.exit("XTTS produced no audio. Try a different text or check reference clips.")
    return np.concatenate(pieces[:-1])   # drop trailing silence


# --------------------------------------------------------------------------- #
# post-processing
# --------------------------------------------------------------------------- #
def load_profile(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _avg_spectrum(y, n_fft=2048, hop=512):
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    db = librosa.amplitude_to_db(
        librosa.feature.rms(S=S, frame_length=n_fft, hop_length=hop)[0] + 1e-9
    )
    active = db > np.percentile(db, 95) - 25
    return np.mean(S[:, active], axis=1) if active.any() else np.mean(S, axis=1)


def match_timbre_eq(y, sr, ref_y):
    """Gentle smooth EQ so the long-term spectrum matches the original voice."""
    diff_db = 20 * np.log10((_avg_spectrum(ref_y) + 1e-8) / (_avg_spectrum(y) + 1e-8))
    diff_db = uniform_filter1d(diff_db, size=33, mode="nearest")
    freqs = np.linspace(0, sr / 2, diff_db.size)
    band = np.clip((freqs - 80) / 200, 0, 1) * np.clip((7500 - freqs) / 500, 0, 1)
    gain_db = np.clip(diff_db * EQ_STRENGTH, -EQ_MAX_DB, EQ_MAX_DB) * band

    n_fft, hop = 2048, 512
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    out = librosa.istft(S * (10 ** (gain_db / 20))[:, None], hop_length=hop, length=len(y))
    return out.astype(np.float32), float(np.max(np.abs(gain_db)))


def match_loudness(y, target_db, limit=8.0):
    gain_db = float(np.clip(target_db - active_db_mean(y), -limit, limit))
    return (y * (10 ** (gain_db / 20))).astype(np.float32), gain_db


def postprocess(y, profile, ref_y, target_db=None):
    """Voice-only processing. target_db overrides the loudness stored in the profile."""
    report = {}
    y = highpass(y, SYNTH_SR)
    y = (y / (np.max(np.abs(y)) or 1.0) * 0.95).astype(np.float32)

    if MATCH_TIMBRE_EQ:
        y, max_db = match_timbre_eq(y, SYNTH_SR, ref_y)
        report["timbre_eq_max_change_db"] = round(max_db, 2)

    if MATCH_LOUDNESS:
        if target_db is not None:                      # level of the voice in the original recording
            y, gain = match_loudness(y, target_db, limit=30.0)
            report["loudness_gain_db"] = round(gain, 2)
        else:
            el = profile.get("energy_loudness", {})
            target = el.get("speech_loudness_db_mean", el.get("loudness_db_mean"))
            if target is not None:
                y, gain = match_loudness(y, target)
                report["loudness_gain_db"] = round(gain, 2)

    peak = np.max(np.abs(y)) or 1.0
    if peak > 0.98:
        y = y / peak * 0.98
    return y.astype(np.float32), report


# --------------------------------------------------------------------------- #
# background preservation (untouched re-mix of the stem saved by main.py)
# --------------------------------------------------------------------------- #
BG_SR = 44100  # background stem rate (set by main.py)


def load_background(profile, profile_path, override=None):
    """Return (background (T, 2) float32, voice level dB in the original recording)."""
    info = profile.get("background") or {}
    stored = info.get("background_wav") or profile.get("files", {}).get("background_wav")
    candidates = [override] if override else []
    if stored:
        candidates += [stored, os.path.join(os.path.dirname(os.path.abspath(profile_path)),
                                            os.path.basename(stored))]
    for p in candidates:
        if p and os.path.isfile(p):
            bg, sr = sf.read(p, dtype="float32", always_2d=True)
            if sr != BG_SR:
                bg = librosa.resample(bg.T, orig_sr=sr, target_sr=BG_SR).T
            if bg.shape[1] == 1:
                bg = np.repeat(bg, 2, axis=1)
            print(f"Background loaded   : {p} ({len(bg) / BG_SR:.1f}s)")
            return np.ascontiguousarray(bg[:, :2]), info.get("voice_level_db_in_original")
    sys.exit("No background audio found in the voice profile.\n"
             "Re-run main.py (it now saves voice_profile_background.wav), "
             "or run this script with --no-background.")


def fit_background(bg, n):
    """Return the background (T, 2) lengthened to n samples. Never altered otherwise."""
    T = bg.shape[0]
    if n <= T:
        return bg[:n]
    if BACKGROUND_FIT == "silence":
        return np.concatenate([bg, np.zeros((n - T, bg.shape[1]), np.float32)])
    # The first pass stays bit-exact; only repeated copies get a 20 ms fade-in (no click at the seam).
    xf = max(1, min(int(0.02 * BG_SR), T // 4))
    fade = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    parts, total = [bg], T
    while total < n:
        c = bg.copy()
        c[:xf] *= fade
        parts.append(c)
        total += T
    return np.concatenate(parts)[:n]


def mix_with_background(voice_24k, bg, start_sec=0.0):
    """Add the (processed) cloned voice on top of the untouched background at the original start offset."""
    voice = librosa.resample(voice_24k, orig_sr=SYNTH_SR, target_sr=BG_SR).astype(np.float32)
    start_pad = max(0, int(round(start_sec * BG_SR)))
    if start_pad > 0:
        voice = np.pad(voice, (start_pad, 0))
    n = max(len(voice), bg.shape[0])                 # keep the whole background
    voice = np.pad(voice, (0, n - len(voice)))
    mix = fit_background(bg, n) + voice[:, None]
    peak = float(np.max(np.abs(mix)))
    gain_db = 0.0
    if peak > 0.99:                                  # one global gain: balance stays identical
        g = 0.99 / peak
        mix = mix * g
        gain_db = 20 * float(np.log10(g))
    return mix.astype(np.float32), gain_db


# --------------------------------------------------------------------------- #
# energy graph
# --------------------------------------------------------------------------- #
def analyze(y, sr):
    y22 = librosa.resample(y, orig_sr=sr, target_sr=22050) if sr != 22050 else y
    hop = 256
    rms = librosa.feature.rms(y=y22, frame_length=2048, hop_length=hop)[0]
    db = np.maximum(librosa.amplitude_to_db(rms + 1e-9), -80.0)
    f0, _, _ = librosa.pyin(y22, fmin=65, fmax=500, sr=22050, frame_length=2048, hop_length=hop)
    return {
        "speech_db": active_db_mean(y22),
        "t": librosa.times_like(rms, sr=22050, hop_length=hop), "db": db,
        "tf": librosa.times_like(f0, sr=22050, hop_length=hop), "f0": f0,
    }


def save_energy_graph(ref, gen, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    blue, red = "#4C72B0", "#C44E52"
    fig, ax = plt.subplots(4, 1, figsize=(13, 13))
    for a, c, color, name in ((ax[0], ref, blue, "ORIGINAL voice (reference)"),
                              (ax[1], gen, red, "CLONED voice")):
        sm = uniform_filter1d(c["db"], 7)
        a.fill_between(c["t"], -80, sm, color=color, alpha=0.25)
        a.plot(c["t"], c["db"], color="#B0B0B0", lw=0.7)
        a.plot(c["t"], sm, color=color, lw=1.6)
        a.axhline(c["speech_db"], ls="--", color="black", lw=0.9)
        a.set_title(f"{name} - energy (mean speech {c['speech_db']:.1f} dB)", fontsize=11)
        a.set_ylabel("Energy (dB)")
        a.set_xlabel("Time (s)")
        a.set_ylim(-80, 0)

    grid = np.linspace(0, 100, 500)
    for c, color, label in ((ref, blue, "original"), (gen, red, "cloned")):
        ax[2].plot(grid, np.interp(grid, c["t"] / c["t"][-1] * 100, uniform_filter1d(c["db"], 9)),
                   color=color, lw=1.8, label=label)
        ax[3].plot(c["tf"] / c["tf"][-1] * 100, c["f0"], ".", ms=2.5, color=color, alpha=0.6, label=label)
    ax[2].set_title("Energy overlay (time normalised to 0-100 %)", fontsize=11)
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


# --------------------------------------------------------------------------- #
# export
# --------------------------------------------------------------------------- #
def save_output(y, sr, wav_path, mp3_path):
    """Save both WAV and MP3.  Returns (wav_path, mp3_path_or_None)."""
    sf.write(wav_path, y, sr)
    print(f"  WAV saved: {wav_path}")

    mp3_ok = None
    try:
        from pydub import AudioSegment
        AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3", bitrate="192k")
        mp3_ok = mp3_path
        print(f"  MP3 saved: {mp3_path}")
    except Exception:
        try:
            sf.write(mp3_path, y, sr, format="MP3")
            mp3_ok = mp3_path
            print(f"  MP3 saved: {mp3_path}")
        except Exception as exc:
            print(f"  MP3 export failed ({exc}). Install ffmpeg + pydub.")
    return wav_path, mp3_ok


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Speak any text in the author's cloned voice.")
    parser.add_argument("text", nargs="?", default=None, help="Text to speak")
    parser.add_argument("--text", dest="text_arg", default=None, help="Text to speak")
    parser.add_argument("--text-file", default=None, help="Path to text file to speak")
    parser.add_argument("--language", default=LANGUAGE, help="Language code or 'auto'")
    parser.add_argument("--profile", default=PROFILE_JSON, help="Path to voice_profile.json")
    parser.add_argument("--reference", default=REFERENCE_WAV, help="Path to voice_profile_reference.wav")
    parser.add_argument("--clips-dir", default=CLIPS_DIR, help="Path to voice_profile_clips folder")
    parser.add_argument("--latents-cache", default=LATENTS_CACHE, help="Path to voice_latents.pt")
    parser.add_argument("--output-mp3", default=OUTPUT_MP3, help="Path for output MP3")
    parser.add_argument("--output-wav", default=OUTPUT_WAV, help="Path for output WAV")
    parser.add_argument("--target-duration", type=float, default=TARGET_DURATION_SEC, help="Target duration in seconds")
    parser.add_argument("--speed", type=float, default=SPEED, help="Initial speech speed rate")
    parser.add_argument("--no-background", action="store_true", help="Do not add the original background sound")
    parser.add_argument("--background-wav", default=None, help="Background stem to use (default: from the profile)")
    parser.add_argument("--voice-only-wav", default=OUTPUT_VOICE_ONLY_WAV, help="Path for the voice-only output")
    args = parser.parse_args()

    # Determine input text
    raw_text = INPUT_TEXT
    if args.text_file and os.path.isfile(args.text_file):
        with open(args.text_file, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
    elif args.text_arg:
        raw_text = args.text_arg.strip()
    elif args.text:
        raw_text = args.text.strip()

    profile_path = args.profile
    ref_wav_path = args.reference
    clips_folder = args.clips_dir
    cache_path = args.latents_cache
    mp3_out_path = args.output_mp3
    wav_out_path = args.output_wav
    lang_setting = args.language
    target_dur = args.target_duration
    speech_speed = args.speed

    for p in (profile_path, ref_wav_path):
        if not os.path.isfile(p):
            sys.exit(f"Missing file: {p}\nRun 'python main.py' first to extract the voice profile.")
    if not raw_text.strip():
        sys.exit("INPUT_TEXT is empty. Set it in the SETTINGS block at the top of the file or pass --text / --text-file.")

    lang = resolve_language(raw_text, lang_setting)
    text = normalize_text(raw_text, lang)
    profile = load_profile(profile_path)
    print(f"Voice profile loaded: {profile_path}")
    print(f"Language used       : {lang}" + ("  (auto-detected)" if lang_setting.lower() == "auto" else ""))

    bg, voice_target_db = None, None
    if PRESERVE_BACKGROUND and not args.no_background:
        bg, voice_target_db = load_background(profile, profile_path, args.background_wav)

    # Determine target duration and timing alignment
    bg_info = profile.get("background", {})
    speech_start_sec = float(bg_info.get("speech_start_sec", 0.0))
    speech_dur_sec = float(bg_info.get("speech_duration_sec", 0.0))
    bg_total_dur = float(bg_info.get("duration_sec", 0.0))

    target = target_dur
    if target is None and MATCH_ORIGINAL_DURATION:
        # Align target speech duration to the active speaking window of the source speaker
        if speech_dur_sec > 0.5:
            target = speech_dur_sec
        else:
            target = profile.get("metadata", {}).get("duration_sec") or bg_total_dur or None


    model, device, torch = load_model()
    gpt, spk = get_voice_embedding(model, device, torch, clips_dir=clips_folder, ref_wav=ref_wav_path, cache_path=cache_path)
    ref_y, _ = librosa.load(ref_wav_path, sr=SYNTH_SR, mono=True)
    ref = reference_stats(profile)

    print(f"\nText to speak ({lang}):\n  \"{text}\"\n")
    print(f"Generating speech ({N_CANDIDATES} candidate(s) per sentence) ...")
    speed = speech_speed
    y = generate_speech(model, torch, text, lang, gpt, spk, ref, speed)

    # ---- length control: make the output about as long as the original ----
    if target:
        dur = len(y) / SYNTH_SR
        print(f"\nGenerated {dur:.1f}s, target {target:.1f}s")
        if abs(dur - target) / target > DURATION_TOLERANCE:
            new_speed = float(np.clip(speed * dur / target, MIN_SPEED, MAX_SPEED))
            if abs(new_speed - speed) > 0.03:
                print(f"Re-generating at speech rate x{new_speed:.2f} to match the original length ...")
                speed = new_speed
                y = generate_speech(model, torch, text, lang, gpt, spk, ref, speed)
                print(f"New length: {len(y) / SYNTH_SR:.1f}s")
            if abs(len(y) / SYNTH_SR - target) / target > 0.25:
                print("NOTE: the text is naturally longer than the original at a natural speech rate "
                      "(e.g. Hindi vs English). Shorten the text, or raise MAX_SPEED slightly.")

    # ---- post-process ----
    print("\nMatching voice features from profile ...")
    y, adjustments = postprocess(y, profile, ref_y, target_db=voice_target_db)
    voice_only = y

    # ---- put the original background back, untouched ----
    out_sr, final = SYNTH_SR, y
    if bg is not None:
        voice_only_dir = os.path.dirname(args.voice_only_wav)
        if voice_only_dir:
            os.makedirs(voice_only_dir, exist_ok=True)
            if sys.platform == "win32" and os.path.basename(voice_only_dir).startswith("."):
                subprocess.run(["attrib", "+h", voice_only_dir], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sf.write(args.voice_only_wav, voice_only, SYNTH_SR)
        final, mix_gain = mix_with_background(voice_only, bg, start_sec=speech_start_sec)
        out_sr = BG_SR
        adjustments["background"] = "original, unprocessed"
        adjustments["speech_start_offset_sec"] = speech_start_sec
        if mix_gain:
            adjustments["overall_gain_db_to_avoid_clipping"] = round(mix_gain, 2)


    # ---- save output ----
    print("\nSaving output ...")
    wav_out_dir = os.path.dirname(wav_out_path)
    if wav_out_dir:
        os.makedirs(wav_out_dir, exist_ok=True)
    if mp3_out_path:
        mp3_out_dir = os.path.dirname(mp3_out_path)
        if mp3_out_dir:
            os.makedirs(mp3_out_dir, exist_ok=True)

    wav_out, mp3_out = save_output(final, out_sr, wav_out_path, mp3_out_path)

    if SAVE_ENERGY_GRAPH:
        try:
            graph_path = ENERGY_GRAPH_PNG
            # If the user specified a specific output dir for wav/mp3, place the graph alongside it
            if wav_out_dir and wav_out_dir != "." and wav_out_dir != DEFAULT_OUTPUT_DIR:
                graph_path = os.path.join(wav_out_dir, os.path.basename(ENERGY_GRAPH_PNG))
            else:
                os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
                if sys.platform == "win32":
                    subprocess.run(["attrib", "+h", DEFAULT_OUTPUT_DIR], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            save_energy_graph(analyze(ref_y, SYNTH_SR), analyze(voice_only, SYNTH_SR), graph_path)
            print(f"  Graph saved: {graph_path}")
        except Exception as exc:
            print(f"  Energy graph skipped ({exc})")

    print(f"\n{'=' * 50}")
    print(f"  Language        : {lang}")
    print(f"  Duration        : {len(final) / out_sr:.1f}s" + (f" (original {target:.1f}s)" if target else ""))
    if bg is not None:
        print(f"  Background      : original kept untouched")
        print(f"  Voice only      : {args.voice_only_wav}")
    print(f"  Speech rate     : x{speed:.2f}")
    print(f"  Adjustments     : {adjustments}")
    print(f"  WAV output      : {wav_out}")
    if mp3_out:
        print(f"  MP3 output      : {mp3_out}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()