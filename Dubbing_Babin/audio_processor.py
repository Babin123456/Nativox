#!/usr/bin/env python3
"""
audio_processor.py - Vocal Separation, Acoustic Profiling, and Duration Alignment

Responsibilities:
  - Vocal stem separation from background (Demucs htdemucs_ft)
  - Speaker pitch (F0) and RMS energy profiling per segment
  - Pitch-preserving time-stretch to match original speech window (librosa WSOLA)
  - Spectral envelope (formant proxy) transfer via LPC-based EQ
  - Silence padding / trimming to fit target duration exactly

No heavy external dependencies beyond what is in the venv:
  torch, demucs, librosa, numpy, soundfile, scipy
"""
from __future__ import annotations

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
import librosa
import soundfile as sf
from scipy import signal


# ---------------------------------------------------------------------------
# Demucs vocal separation
# ---------------------------------------------------------------------------

def separate_vocals(
    audio_path: Path,
    output_dir: Path,
    model: str = "htdemucs_ft",
) -> tuple[Path, Path]:
    """
    Separate vocals and background using Demucs.
    Returns (vocals_wav, background_wav) paths.

    Both are saved as 44100 Hz stereo WAV files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    vocals_out = output_dir / "voice_profile_vocals.wav"
    background_out = output_dir / "voice_profile_background.wav"

    # Check if already separated
    if vocals_out.is_file() and background_out.is_file():
        print(f"[*] Vocal stems already separated, reusing cached files.")
        _write_bg_sidecar(background_out)
        return vocals_out, background_out

    print(f"[*] Running Demucs ({model}) for vocal/background separation...")
    sep_tmp = output_dir / "_demucs_sep"
    sep_tmp.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "demucs",
        "--name", model,
        "--out", str(sep_tmp),
        "--two-stems", "vocals",
        str(audio_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        # Fallback to lighter model if htdemucs_ft fails (e.g., first download)
        print(f"[!] htdemucs_ft failed, retrying with mdx_extra_q ...")
        cmd[3] = "mdx_extra_q"
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"Demucs separation failed: {res.stderr[-400:]}")

    # Demucs writes to: sep_tmp/<model>/<stem_name>/<vocals.wav|no_vocals.wav>
    stem_dirs = list(sep_tmp.rglob("vocals.wav"))
    no_vocals = list(sep_tmp.rglob("no_vocals.wav"))
    if not stem_dirs:
        raise RuntimeError("Demucs did not produce vocals.wav")

    import shutil
    shutil.copy2(str(stem_dirs[0]), str(vocals_out))
    if no_vocals:
        shutil.copy2(str(no_vocals[0]), str(background_out))
    else:
        # Fallback: create silent background of same length
        y, sr = sf.read(str(vocals_out), dtype="float32")
        sf.write(str(background_out), np.zeros_like(y), sr)

    _write_bg_sidecar(background_out)
    print(f"[+] Vocals: {vocals_out.name}  Background: {background_out.name}")
    return vocals_out, background_out


def _write_bg_sidecar(background_out: Path):
    """Write a small JSON sidecar so cloner.py's load_background() can find the file."""
    import json
    sidecar = background_out.with_suffix(".wav.json")
    if not sidecar.is_file():
        sidecar.write_text(
            json.dumps({"background_wav": str(background_out), "voice_level_db_in_original": None}),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Reference clip extraction from vocals stem
# ---------------------------------------------------------------------------

def extract_best_reference_clip(
    vocals_wav: Path,
    clips_dir: Path,
    clip_duration_sec: float = 10.0,
    min_duration_sec: float = 3.0,
) -> Path:
    """
    Extract the loudest / most voiced segment from the separated vocals stem
    to use as the XTTS v2 reference clip. Saves clip_01.wav into clips_dir.
    """
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_out = clips_dir / "clip_01.wav"

    if clip_out.is_file():
        return clip_out

    y, sr = librosa.load(str(vocals_wav), sr=24000, mono=True)
    if len(y) == 0:
        sf.write(str(clip_out), y, sr)
        return clip_out

    target_len = int(clip_duration_sec * sr)
    if len(y) <= target_len:
        # Whole file is shorter than target clip; use as-is
        sf.write(str(clip_out), y, sr)
        return clip_out

    # Pick the window with the highest RMS energy (most active speech)
    hop = int(0.5 * sr)
    best_start = 0
    best_rms = -1.0
    for start in range(0, len(y) - target_len, hop):
        chunk = y[start: start + target_len]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms > best_rms:
            best_rms = rms
            best_start = start

    clip = y[best_start: best_start + target_len]
    sf.write(str(clip_out), clip, sr)
    print(f"[+] Reference clip extracted: {clip_out.name} ({clip_duration_sec:.1f}s, RMS={best_rms:.4f})")
    return clip_out


# ---------------------------------------------------------------------------
# Pitch (F0) profiling
# ---------------------------------------------------------------------------

def profile_pitch(audio_path: Path, sr: int = 22050) -> dict:
    """
    Returns basic F0 stats for the audio:
      median_f0_hz, std_f0_hz, gender ('male'|'female')
    """
    y, _ = librosa.load(str(audio_path), sr=sr, mono=True)
    if len(y) < sr // 4:
        return {"median_f0_hz": 150.0, "std_f0_hz": 20.0, "gender": "male"}

    f0, _, _ = librosa.pyin(
        y, fmin=65.0, fmax=500.0, sr=sr,
        frame_length=2048, hop_length=256,
    )
    voiced = f0[~np.isnan(f0)]
    if voiced.size < 5:
        return {"median_f0_hz": 150.0, "std_f0_hz": 20.0, "gender": "male"}

    med = float(np.median(voiced))
    std = float(np.std(voiced))
    gender = "female" if med > 165.0 else "male"
    print(f"[*] Speaker pitch profile: median F0={med:.1f} Hz, std={std:.1f} Hz, gender={gender}")
    return {"median_f0_hz": med, "std_f0_hz": std, "gender": gender}


# ---------------------------------------------------------------------------
# Duration-precise time stretching
# ---------------------------------------------------------------------------

def stretch_to_duration(
    y: np.ndarray,
    sr: int,
    target_seconds: float,
    min_rate: float = 0.72,
    max_rate: float = 1.40,
) -> np.ndarray:
    """
    Pitch-preserving time stretch (librosa WSOLA) to fit y into target_seconds.
    Rate is clamped to [min_rate, max_rate] to avoid extreme distortion.
    If rate is already within 2% of 1.0 no stretch is applied.
    """
    current_dur = len(y) / sr
    if target_seconds <= 0 or current_dur <= 0:
        return y

    rate = float(np.clip(current_dur / target_seconds, min_rate, max_rate))
    if abs(rate - 1.0) < 0.02:
        return y

    print(f"[*] Time-stretch: {current_dur:.2f}s -> {target_seconds:.2f}s (rate={rate:.3f})")
    stretched = librosa.effects.time_stretch(y.astype(np.float32), rate=rate)

    # Hard-trim or zero-pad to hit the exact target sample count
    target_samples = int(round(target_seconds * sr))
    if len(stretched) > target_samples:
        stretched = stretched[:target_samples]
    elif len(stretched) < target_samples:
        stretched = np.pad(stretched, (0, target_samples - len(stretched)))

    return stretched.astype(np.float32)


# ---------------------------------------------------------------------------
# Spectral envelope matching (simple EQ approach via LPC-based formant proxy)
# ---------------------------------------------------------------------------

def _avg_spectrum(y: np.ndarray, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop))
    rms_per_frame = np.sqrt(np.mean(S ** 2, axis=0))
    # weight by frame loudness — focus on speech-active frames
    threshold = np.percentile(rms_per_frame, 60)
    active = rms_per_frame >= threshold
    if not active.any():
        return np.mean(S, axis=1)
    return np.mean(S[:, active], axis=1)


def apply_spectral_envelope_match(
    y: np.ndarray,
    ref_y: np.ndarray,
    sr: int,
    strength: float = 0.65,
    max_db: float = 5.0,
) -> np.ndarray:
    """
    Gently match the spectral envelope (timbre) of y towards ref_y.
    Operates in the speech band (120 Hz to 7 kHz).
    """
    if len(y) < 512 or len(ref_y) < 512:
        return y

    n_fft = 2048
    hop = 512
    target_spec = _avg_spectrum(ref_y, n_fft, hop)
    source_spec = _avg_spectrum(y, n_fft, hop)

    # Avoid division by zero
    diff_db = 20.0 * np.log10(
        (target_spec + 1e-9) / (source_spec + 1e-9)
    )

    # Smooth the correction curve
    from scipy.ndimage import uniform_filter1d
    diff_db = uniform_filter1d(diff_db, size=35, mode="nearest")

    # Build a band mask: apply correction only in the speech band
    freqs = np.linspace(0, sr / 2, diff_db.size)
    lo_ramp = np.clip((freqs - 120.0) / 200.0, 0.0, 1.0)
    hi_ramp = np.clip((8000.0 - freqs) / 1000.0, 0.0, 1.0)
    band_mask = lo_ramp * hi_ramp

    gain_db = np.clip(diff_db * strength, -max_db, max_db) * band_mask

    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    gain_lin = 10.0 ** (gain_db / 20.0)
    out = librosa.istft(S * gain_lin[:, None], hop_length=hop, length=len(y))
    return out.astype(np.float32)


# ---------------------------------------------------------------------------
# RMS energy matching (loudness normalization)
# ---------------------------------------------------------------------------

def match_loudness(
    y: np.ndarray,
    ref_y: np.ndarray,
    limit_db: float = 18.0,
) -> np.ndarray:
    """Scale y so its active-speech RMS matches ref_y."""
    def _speech_rms(sig):
        rms = librosa.feature.rms(y=sig, frame_length=2048, hop_length=256)[0]
        db = librosa.amplitude_to_db(rms + 1e-9, ref=1.0)
        active = db[db > np.percentile(db, 70)]
        return float(np.mean(10 ** (active / 20))) if active.size else 1e-5

    src_rms = _speech_rms(y)
    ref_rms = _speech_rms(ref_y)
    if src_rms < 1e-9:
        return y

    gain = float(np.clip(ref_rms / src_rms, 10 ** (-limit_db / 20), 10 ** (limit_db / 20)))
    out = (y * gain).astype(np.float32)
    # Hard limiter
    peak = float(np.max(np.abs(out)))
    if peak > 0.98:
        out = out * (0.98 / peak)
    return out


# ---------------------------------------------------------------------------
# Mix voice with background
# ---------------------------------------------------------------------------

def mix_voice_with_background(
    voice_y: np.ndarray,
    voice_sr: int,
    background_path: Optional[Path],
    video_duration: float,
    speech_start_sec: float = 0.0,
) -> tuple[np.ndarray, int]:
    """
    Mix the processed voice onto the original background track.
    Returns (mixed_audio, sample_rate).
    """
    BG_SR = 44100

    # Resample voice to BG_SR stereo
    voice_44k = librosa.resample(voice_y, orig_sr=voice_sr, target_sr=BG_SR)
    if voice_44k.ndim == 1:
        voice_44k = np.stack([voice_44k, voice_44k])  # (2, N)
    elif voice_44k.shape[0] > 2:
        voice_44k = voice_44k[:2]

    # Total output samples
    total_samples = int(round(video_duration * BG_SR))
    if total_samples <= 0:
        total_samples = voice_44k.shape[1]

    # Pad/trim voice to total_samples
    start_pad = int(round(speech_start_sec * BG_SR))
    n_voice_padded = start_pad + voice_44k.shape[1]
    if n_voice_padded > total_samples:
        voice_44k = voice_44k[:, :total_samples - start_pad]
        n_voice_padded = total_samples

    voice_buf = np.zeros((2, total_samples), dtype=np.float32)
    voice_buf[:, start_pad: start_pad + voice_44k.shape[1]] = voice_44k

    if background_path and Path(background_path).is_file():
        bg, bg_sr = sf.read(str(background_path), dtype="float32", always_2d=True)
        bg = bg.T  # -> (channels, samples)
        if bg_sr != BG_SR:
            bg = librosa.resample(bg, orig_sr=bg_sr, target_sr=BG_SR)
        if bg.shape[0] == 1:
            bg = np.vstack([bg, bg])
        elif bg.shape[0] > 2:
            bg = bg[:2]

        # Loop background if shorter than video
        if bg.shape[1] < total_samples:
            repeats = int(np.ceil(total_samples / bg.shape[1]))
            bg = np.tile(bg, (1, repeats))
        bg = bg[:, :total_samples]

        mixed = bg + voice_buf
    else:
        mixed = voice_buf

    # Normalize to avoid clipping
    peak = float(np.max(np.abs(mixed)))
    if peak > 0.98:
        mixed = mixed * (0.98 / peak)

    return mixed.astype(np.float32), BG_SR
