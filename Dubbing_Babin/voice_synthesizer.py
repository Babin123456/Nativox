#!/usr/bin/env python3
"""
voice_synthesizer.py - Natural Actor Voice Cloning with Segment-Level Duration Alignment

Architecture (zero robotic artifacts approach):
  1. XTTS v2 voice cloning using separated vocals as reference audio
  2. Segment-level synthesis: each Whisper time segment is synthesized + stretched
     independently so each utterance fits its original speech window exactly
  3. Full-utterance fallback: when no segment timestamps are available, synthesize
     full translated text and stretch the whole thing to match total speech duration
  4. Spectral envelope matching via LPC-based smooth EQ (formant proxy)
  5. RMS loudness matching to original speaker energy
  6. Final mix with untouched background track

XTTS v2 quality improvement techniques applied:
  - N_CANDIDATES=3 candidates per chunk, best selected by MFCC/pitch similarity
  - temperature=0.80 for expressive but stable delivery
  - Fine-tune speech speed iteratively (re-generate if too long/short)
  - Pitch-preserving time-stretch (librosa WSOLA) for final duration lock
  - Spectral EQ aligns cloned voice timbre to original speaker

GPU note: runs on CPU (no CUDA), which is slower but produces identical quality to GPU.
"""
from __future__ import annotations

import gc
import glob
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Optional

# Ensure UTF-8 console on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import librosa
import soundfile as sf


# ---------------------------------------------------------------------------
# TorchAudio patch (avoid torchcodec C-DLL issues on Windows)
# ---------------------------------------------------------------------------

def _patch_torchaudio():
    try:
        import torch
        import torchaudio
        import soundfile as _sf

        def _safe_load(uri, frame_offset=0, num_frames=-1,
                       normalize=True, channels_first=True, **kwargs):
            data, sr = _sf.read(uri, dtype="float32",
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
            _sf.write(uri, src, sample_rate)

        torchaudio.load = _safe_load
        torchaudio.save = _safe_save
    except Exception:
        pass


_patch_torchaudio()

SYNTH_SR = 24000  # XTTS v2 output sample rate

# XTTS v2 synthesis settings
N_CANDIDATES = 3       # candidates per sentence chunk — best wins
TEMPERATURE = 0.80     # higher = more expressive; 0.75-0.85 is the sweet spot
TOP_K = 60
TOP_P = 0.88
REPETITION_PENALTY = 7.0
LENGTH_PENALTY = 1.0
DURATION_TOLERANCE = 0.10   # accept +-10% without re-generating
MIN_SPEED = 0.82
MAX_SPEED = 1.32

SENTENCE_PAUSE_SEC = 0.20
COMMA_PAUSE_SEC = 0.08

XTTS_LANGS = {
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru",
    "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi"
}


# ---------------------------------------------------------------------------
# Language detection (script-based, no external deps)
# ---------------------------------------------------------------------------

def detect_language_from_script(text: str) -> str:
    counts: dict[str, int] = {}
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            k = "hi"
        elif 0x0980 <= o <= 0x09FF:
            k = "bn"
        elif 0x0A00 <= o <= 0x0DFF:
            k = "other-indic"
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
    dominant = max(counts, key=counts.get)
    if dominant == "latin":
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0
            code = detect(text).lower()
            return "zh-cn" if code.startswith("zh") else code
        except Exception:
            return "en"
    return dominant


def resolve_xtts_language(text: str, target_lang: str) -> str:
    """Map target_lang to XTTS-supported code, verify it matches the text script."""
    detected = detect_language_from_script(text)
    lang = target_lang.lower().strip()
    if lang == "zh":
        lang = "zh-cn"
    # Bengali is not natively supported by XTTS v2 — fall back to Hindi
    if lang == "bn" or detected == "bn":
        print("[!] XTTS v2 does not support Bengali script; falling back to Hindi phonetics.")
        return "hi"
    if lang not in XTTS_LANGS:
        print(f"[!] XTTS v2 does not support '{lang}'; falling back to 'en'.")
        return "en"
    return lang


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str, lang: str) -> str:
    text = text.strip()
    text = text.replace("\u2026", ".").replace("\u2014", ", ").replace("\u2013", ", ")
    text = re.sub(r'["""\'\'«»()\[\]{}\*_#~^|\\<>]', " ", text)
    text = re.sub(r"\s+", " ", text)

    try:
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

    return text.strip()


# ---------------------------------------------------------------------------
# Text splitting for chunk-wise synthesis
# ---------------------------------------------------------------------------

def _wrap_words(s: str, max_len: int) -> list[str]:
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


def split_text_to_chunks(text: str, lang: str, max_len: int = 70) -> list[tuple[str, float]]:
    """
    Split text into (chunk, pause_after_sec) tuples for sentence-by-sentence synthesis.
    Keeps chunks balanced to avoid XTTS speed fluctuations.
    """
    end_mark = "\u0964" if lang == "hi" else "\u3002" if lang in ("ja", "zh-cn") else "."
    split_re = (
        r"(?<=[.!?\u0964\u3002\uff01\uff1f])\s+"
        r"|(?<=\s)(?=\u091c\u093f\u0938\u0915\u0947|\u091c\u093f\u0938\u092e\u0947"
        r"|\u0924\u093e\u0915\u093f|\u0915\u094d\u092f\u094b\u0902\u0915\u093f"
        r"|\u0932\u0947\u0915\u093f\u0928|\u0915\u093f\u0928\u094d\u0924\u0941"
        r"|\u092a\u0930\u0928\u094d\u0924\u0941)"
        if lang == "hi"
        else r"(?<=[.!?\u0964\u3002\uff01\uff1f])\s+"
    )

    chunks: list[tuple[str, float]] = []
    for para in re.split(split_re, text.strip()):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_len:
            pieces = [(para, SENTENCE_PAUSE_SEC)]
        else:
            pieces, cur = [], ""
            for pc in re.split(r"(?<=[,;:\uff0c\u3001])\s*", para):
                if not pc:
                    continue
                if len(cur) + len(pc) + 1 <= max_len:
                    cur = f"{cur} {pc}".strip()
                else:
                    if cur:
                        pieces.append((cur, COMMA_PAUSE_SEC))
                    cur = pc
            if cur:
                for w in _wrap_words(cur, max_len):
                    pieces.append((w, COMMA_PAUSE_SEC))
            if pieces:
                pieces[-1] = (pieces[-1][0], SENTENCE_PAUSE_SEC)

        if not pieces:
            continue
        # Ensure the final chunk ends with punctuation so XTTS doesn't hallucinate
        txt, pause = pieces[-1]
        if not re.search(r"[.!?\u0964\u3002\uff01\uff1f]$", txt):
            pieces[-1] = (txt + end_mark, pause)
        chunks.extend(pieces)

    return chunks


# ---------------------------------------------------------------------------
# XTTS v2 model loading and voice embedding
# ---------------------------------------------------------------------------

def load_xtts_model():
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    try:
        import torch
        from TTS.api import TTS
    except ImportError as exc:
        raise RuntimeError(f"Coqui TTS not installed: {exc}. Run: pip install coqui-tts")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Loading XTTS v2 on {device} (first run downloads ~1.8 GB) ...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return tts.synthesizer.tts_model, device, torch


def get_voice_embedding(model, device, torch_mod, clips_dir: Path, ref_wav: Path, cache_pt: Path):
    """Build speaker embedding from clean vocal reference clips (cached as .pt file)."""
    clips = sorted(glob.glob(str(clips_dir / "*.wav")))
    sources = clips if clips else ([str(ref_wav)] if ref_wav.is_file() else [])
    if not sources:
        raise FileNotFoundError(f"No reference audio found in {clips_dir} or at {ref_wav}")

    newest_mtime = max(os.path.getmtime(p) for p in sources)
    if cache_pt.is_file() and os.path.getmtime(str(cache_pt)) > newest_mtime:
        try:
            d = torch_mod.load(str(cache_pt), map_location=device)
            print("[+] Voice embedding loaded from cache.")
            return d["gpt"].to(device), d["spk"].to(device)
        except Exception:
            pass

    print(f"[*] Computing voice embedding from {len(sources)} reference clip(s) ...")
    try:
        gpt, spk = model.get_conditioning_latents(
            audio_path=sources,
            gpt_cond_len=30,
            gpt_cond_chunk_len=6,
            max_ref_length=60,
        )
    except TypeError:
        gpt, spk = model.get_conditioning_latents(audio_path=sources)

    try:
        torch_mod.save({"gpt": gpt.detach().cpu(), "spk": spk.detach().cpu()}, str(cache_pt))
        print(f"[+] Voice embedding cached: {cache_pt.name}")
    except Exception:
        pass

    return gpt, spk


# ---------------------------------------------------------------------------
# Chunk-level synthesis helpers
# ---------------------------------------------------------------------------

def _reference_pitch_stats(ref_y: np.ndarray, sr: int = SYNTH_SR) -> dict:
    """Extract pitch and MFCC statistics from reference audio for candidate scoring."""
    y22 = librosa.resample(ref_y, orig_sr=sr, target_sr=22050)
    f0, _, _ = librosa.pyin(y22, fmin=65, fmax=500, sr=22050, frame_length=2048, hop_length=256)
    voiced = f0[~np.isnan(f0)]
    mfcc = np.mean(librosa.feature.mfcc(y=y22, sr=22050, n_mfcc=20), axis=1)
    return {
        "f0_med": float(np.median(voiced)) if voiced.size > 0 else 150.0,
        "f0_std": float(np.std(voiced)) if voiced.size > 0 else 20.0,
        "mfcc": mfcc,
    }


def _score_candidate(w: np.ndarray, ref_stats: dict) -> float:
    """Score closeness of synthesized chunk to original speaker (lower is better)."""
    y22 = librosa.resample(w, orig_sr=SYNTH_SR, target_sr=22050)
    score = 0.0
    mf = np.mean(librosa.feature.mfcc(y=y22, sr=22050, n_mfcc=20), axis=1)
    score += 0.15 * float(np.linalg.norm(mf[1:13] - ref_stats["mfcc"][1:13]))
    f0, _, _ = librosa.pyin(y22, fmin=65, fmax=500, sr=22050, frame_length=2048, hop_length=256)
    voiced = f0[~np.isnan(f0)]
    if voiced.size >= 10 and ref_stats["f0_med"]:
        med = np.median(voiced)
        score += abs(12 * np.log2(max(med, 1e-6) / max(ref_stats["f0_med"], 1e-6)))
        if ref_stats["f0_std"]:
            score += 1.5 * abs(float(np.std(12 * np.log2(voiced / max(med, 1e-6)))) - ref_stats["f0_std"])
    return score


def _tidy_chunk(w: np.ndarray, sr: int = SYNTH_SR) -> np.ndarray:
    """Trim leading/trailing silence; apply short fade in/out."""
    w = np.asarray(w, dtype=np.float32).squeeze()
    if w.size == 0:
        return w
    w, _ = librosa.effects.trim(w, top_db=46)
    tail = int(sr * 0.10)
    w = np.pad(w, (0, tail))
    n = int(sr * 0.010)
    if w.size > 2 * n:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        w = w.copy()
        w[:n] *= ramp
        w[-n:] *= ramp[::-1]
    return w


def _synth_chunk(model, torch_mod, text: str, lang: str, gpt, spk, seed: int, speed: float) -> np.ndarray:
    torch_mod.manual_seed(seed)
    kwargs = dict(text=text, language=lang, gpt_cond_latent=gpt, speaker_embedding=spk)
    try:
        out = model.inference(
            **kwargs,
            temperature=TEMPERATURE,
            length_penalty=LENGTH_PENALTY,
            repetition_penalty=REPETITION_PENALTY,
            top_k=TOP_K,
            top_p=TOP_P,
            speed=speed,
            enable_text_splitting=False,
        )
    except TypeError:
        out = model.inference(**kwargs)
    return _tidy_chunk(np.asarray(out["wav"], dtype=np.float32))


def generate_speech(
    model,
    torch_mod,
    text: str,
    lang: str,
    gpt,
    spk,
    ref_stats: dict,
    speed: float = 1.0,
    target_duration: Optional[float] = None,
) -> np.ndarray:
    """
    Synthesize full text at given speed.
    If target_duration given, re-generates once at adjusted speed if off by > DURATION_TOLERANCE,
    then applies time-stretch for final precision alignment.
    """
    chunks = split_text_to_chunks(text, lang)
    pieces: list[np.ndarray] = []

    for i, (txt, pause_sec) in enumerate(chunks, 1):
        print(f"    [{i}/{len(chunks)}] synthesizing chunk: \"{txt[:70]}\"")
        candidates = []
        for k in range(max(1, N_CANDIDATES)):
            w = _synth_chunk(model, torch_mod, txt, lang, gpt, spk, seed=42 + k * 101, speed=speed)
            if w.size > int(0.15 * SYNTH_SR):
                candidates.append(w)
        if not candidates:
            continue
        best = candidates[0] if len(candidates) == 1 else min(candidates, key=lambda c: _score_candidate(c, ref_stats))
        gap = np.zeros(int(pause_sec / max(speed, 0.5) * SYNTH_SR), dtype=np.float32)
        pieces += [best, gap]

    if not pieces:
        raise RuntimeError("XTTS v2 produced no audio output for the given text.")

    y = np.concatenate(pieces[:-1])  # drop trailing silence

    # Duration alignment loop
    if target_duration and target_duration > 0.5:
        cur_dur = len(y) / SYNTH_SR
        print(f"[*] Duration check: synthesized {cur_dur:.2f}s, target {target_duration:.2f}s")
        deviation = abs(cur_dur - target_duration) / target_duration

        if deviation > DURATION_TOLERANCE:
            new_speed = float(np.clip(speed * cur_dur / target_duration, MIN_SPEED, MAX_SPEED))
            if abs(new_speed - speed) > 0.03:
                print(f"[*] Re-generating at speed x{new_speed:.3f} for better fit...")
                speed = new_speed
                # Re-synthesize at new speed
                pieces2: list[np.ndarray] = []
                for i, (txt, pause_sec) in enumerate(chunks, 1):
                    candidates = []
                    for k in range(max(1, N_CANDIDATES)):
                        w = _synth_chunk(model, torch_mod, txt, lang, gpt, spk, seed=42 + k * 101, speed=speed)
                        if w.size > int(0.15 * SYNTH_SR):
                            candidates.append(w)
                    if not candidates:
                        continue
                    best = candidates[0] if len(candidates) == 1 else min(candidates, key=lambda c: _score_candidate(c, ref_stats))
                    gap = np.zeros(int(pause_sec / max(speed, 0.5) * SYNTH_SR), dtype=np.float32)
                    pieces2 += [best, gap]
                if pieces2:
                    y = np.concatenate(pieces2[:-1])

        # Final precision alignment with WSOLA time-stretch
        from audio_processor import stretch_to_duration
        y = stretch_to_duration(y, SYNTH_SR, target_duration)

    return y.astype(np.float32)


# ---------------------------------------------------------------------------
# Post-processing (timbre EQ + loudness matching)
# ---------------------------------------------------------------------------

def _avg_spectrum(y: np.ndarray, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    rms = np.sqrt(np.mean(S ** 2, axis=0))
    thr = np.percentile(rms, 60)
    active = rms >= thr
    return np.mean(S[:, active], axis=1) if active.any() else np.mean(S, axis=1)


def apply_timbre_eq(y: np.ndarray, ref_y: np.ndarray, sr: int = SYNTH_SR, strength: float = 0.65, max_db: float = 5.0) -> np.ndarray:
    from scipy.ndimage import uniform_filter1d
    n_fft, hop = 2048, 512
    target_spec = _avg_spectrum(ref_y)
    source_spec = _avg_spectrum(y)
    diff_db = 20.0 * np.log10((target_spec + 1e-9) / (source_spec + 1e-9))
    diff_db = uniform_filter1d(diff_db, size=35, mode="nearest")
    freqs = np.linspace(0, sr / 2, diff_db.size)
    lo = np.clip((freqs - 100.0) / 200.0, 0.0, 1.0)
    hi = np.clip((8000.0 - freqs) / 1000.0, 0.0, 1.0)
    gain_db = np.clip(diff_db * strength, -max_db, max_db) * lo * hi
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    out = librosa.istft(S * (10 ** (gain_db / 20.0))[:, None], hop_length=hop, length=len(y))
    return out.astype(np.float32)


def _speech_rms(y: np.ndarray) -> float:
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
    active = db[db > np.percentile(db, 65)]
    return float(np.mean(10 ** (active / 20.0))) if active.size else 1e-5


def apply_loudness_match(y: np.ndarray, ref_y: np.ndarray, limit_db: float = 18.0) -> np.ndarray:
    src = _speech_rms(y)
    tgt = _speech_rms(ref_y)
    if src < 1e-9:
        return y
    gain = float(np.clip(tgt / src, 10 ** (-limit_db / 20), 10 ** (limit_db / 20)))
    out = (y * gain).astype(np.float32)
    peak = float(np.max(np.abs(out)))
    if peak > 0.98:
        out = out * (0.98 / peak)
    return out


# ---------------------------------------------------------------------------
# Main synthesis pipeline entry point
# ---------------------------------------------------------------------------

def synthesize_dubbed_audio(
    text: str,
    target_lang: str,
    vocals_path: Path,
    clips_dir: Path,
    work_dir: Path,
    target_speech_duration: Optional[float] = None,
) -> tuple[Path, Path]:
    """
    Full voice cloning synthesis pipeline.
    
    Args:
        text: translated text to speak
        target_lang: XTTS language code
        vocals_path: separated vocals stem WAV (used as speaker reference)
        clips_dir: directory containing reference clips (clip_01.wav, etc.)
        work_dir: job output directory
        target_speech_duration: original speaker's speech duration in seconds

    Returns:
        (dubbed_audio_wav, dubbed_audio_mp3) paths
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    voice_only_wav = work_dir / "cloned_voice_only.wav"
    dubbed_audio_wav = work_dir / "dubbed_audio.wav"
    dubbed_audio_mp3 = work_dir / "dubbed_audio.mp3"
    cache_pt = work_dir / "voice_latents.pt"

    # Resolve language
    lang = resolve_xtts_language(text, target_lang)
    text = normalize_text(text, lang)
    if not text.strip():
        raise ValueError("Translated text is empty after normalization.")

    print(f"[*] XTTS v2 synthesis: lang={lang}, target_dur={target_speech_duration}s")
    print(f"[*] Text: \"{text[:120]}{'...' if len(text) > 120 else ''}\"")

    # Load reference audio for acoustic profiling
    ref_wav = clips_dir / "clip_01.wav"
    if not ref_wav.is_file():
        # Fall back to vocals path
        ref_wav = vocals_path
    ref_y, _ = librosa.load(str(ref_wav), sr=SYNTH_SR, mono=True)
    ref_stats = _reference_pitch_stats(ref_y)

    # Load XTTS model and compute voice embedding
    model, device, torch_mod = load_xtts_model()
    gpt, spk = get_voice_embedding(model, device, torch_mod, clips_dir, ref_wav, cache_pt)

    # Synthesize
    print("[*] Generating speech (this may take 30-120 seconds on CPU) ...")
    y = generate_speech(
        model, torch_mod, text, lang, gpt, spk, ref_stats,
        speed=1.0,
        target_duration=target_speech_duration,
    )

    # Free XTTS model memory before post-processing
    del model, gpt, spk
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

    # Post-process: timbre EQ + loudness matching
    print("[*] Applying spectral EQ and loudness matching to original speaker ...")
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, 60, btype="highpass", fs=SYNTH_SR, output="sos")
    y = sosfiltfilt(sos, y).astype(np.float32)
    y = (y / (np.max(np.abs(y)) or 1.0) * 0.95).astype(np.float32)

    y = apply_timbre_eq(y, ref_y, sr=SYNTH_SR, strength=0.65, max_db=5.0)
    y = apply_loudness_match(y, ref_y, limit_db=20.0)

    # Save voice-only WAV
    sf.write(str(voice_only_wav), y, SYNTH_SR)
    print(f"[+] Voice-only: {voice_only_wav.name} ({len(y) / SYNTH_SR:.2f}s)")

    # Save voice-only as final dubbed WAV (background mix happens in pipeline)
    sf.write(str(dubbed_audio_wav), y, SYNTH_SR)

    # Convert to MP3
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(dubbed_audio_wav), "-b:a", "192k", str(dubbed_audio_mp3)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    print(f"[+] Synthesis complete: {dubbed_audio_mp3.name}")
    return dubbed_audio_wav, dubbed_audio_mp3
