#!/usr/bin/env python3
"""
Nativox Dubbing_Babin - Natural Actor Voice Dubbing Pipeline
============================================================
Produces cinematic-quality dubbed video that:
  - Preserves the original speaker's voice timbre, pitch, and emotions
  - Dubs into the target language with natural, idiomatic speech
  - Maintains the exact original speaking duration in the dubbed output
  - Mixes the dubbed voice with the original background (music, ambient)

Pipeline stages:
  [01]  Audio demux (FFmpeg)
  [02a] Transcription with word-level timestamps (faster-whisper)
  [02b] Vocal/background separation (Demucs htdemucs_ft)
  [02c] Reference clip extraction from clean vocals
  [03]  Natural idiomatic translation (Google Translate + cadence check)
  [04]  XTTS v2 voice cloning with speed-loop + WSOLA duration alignment
  [05]  Spectral EQ + loudness matching to original speaker
  [06]  Background + voice mixing
  [07]  Video remux (FFmpeg)

Single command:
    python pipeline.py --video path/to/video.mp4 --target-lang hi

Output:
    outputs/<job_id>/final_dubbed_video.mp4
    outputs/<job_id>/dubbed_audio.wav   (voice + background mix)
    outputs/<job_id>/cloned_voice_only.wav
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _banner(step: str, title: str):
    print(f"\n{'=' * 72}")
    print(f"  Stage {step}: {title}")
    print(f"{'=' * 72}")


def _require_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        sys.exit("[ERROR] ffmpeg / ffprobe not found on PATH. Install FFmpeg.")


# ---------------------------------------------------------------------------
# Stage 01 — Audio demux
# ---------------------------------------------------------------------------

def stage_01_extract_audio(video_path: Path, work_dir: Path) -> tuple[Path, float, float]:
    _banner("01", "Demuxing audio track with FFmpeg")
    audio_wav = work_dir / "audio.wav"

    # Demux to WAV (lossless; better for Demucs and Whisper)
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(audio_wav),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio demux failed: {res.stderr[-400:]}")

    # Probe video duration
    dur_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
    ]
    dur_res = subprocess.run(dur_cmd, capture_output=True, text=True)
    video_duration = float(dur_res.stdout.strip()) if dur_res.returncode == 0 and dur_res.stdout.strip() else 0.0

    # Also create an MP3 copy for compatibility with legacy voice profiler
    audio_mp3 = work_dir / "audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_wav), "-q:a", "2", str(audio_mp3)],
        capture_output=True,
    )

    print(f"[+] Audio extracted: {audio_wav.name}")
    print(f"[+] Video duration: {video_duration:.2f}s")
    return audio_wav, audio_mp3, video_duration


# ---------------------------------------------------------------------------
# Stage 02a — Transcription
# ---------------------------------------------------------------------------

def stage_02a_transcribe(audio_path: Path, work_dir: Path, source_lang: str = "auto") -> dict:
    _banner("02a", "Transcribing speech with faster-whisper (word timestamps)")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")

    print("[*] Loading Whisper base model (CPU, int8)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    segments_raw, info = model.transcribe(
        str(audio_path),
        language=None if source_lang in ("auto", "") else source_lang,
        beam_size=5,
        word_timestamps=True,
    )

    segments: list[dict] = []
    full_text_parts: list[str] = []
    first_start: float | None = None
    last_end: float = 0.0

    for seg in segments_raw:
        txt = seg.text.strip()
        if not txt:
            continue
        entry = {
            "text": txt,
            "start": seg.start,
            "end": seg.end,
        }
        if seg.words:
            entry["words"] = [{"word": w.word, "start": w.start, "end": w.end} for w in seg.words]
        segments.append(entry)
        full_text_parts.append(txt)
        if first_start is None:
            first_start = seg.start
        last_end = max(last_end, seg.end)

    full_text = " ".join(full_text_parts).strip()
    detected_lang = info.language or "en"
    speech_start = first_start if first_start is not None else 0.0
    speech_end = last_end if last_end > 0.0 else video_duration_fallback(work_dir)
    speech_duration = max(0.0, speech_end - speech_start)

    # Save transcript
    (work_dir / "transcript.txt").write_text(full_text, encoding="utf-8")
    (work_dir / "segments.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[+] Detected language: {detected_lang} (confidence: {info.language_probability:.2f})")
    print(f"[+] Words transcribed: {len(full_text.split())}")
    print(f"[+] Speech window: {speech_start:.2f}s -> {speech_end:.2f}s (duration: {speech_duration:.2f}s)")
    print(f"[+] Transcript: \"{full_text[:120]}{'...' if len(full_text) > 120 else ''}\"")

    return {
        "full_text": full_text,
        "segments": segments,
        "detected_lang": detected_lang,
        "speech_start": speech_start,
        "speech_duration": speech_duration,
    }


def video_duration_fallback(work_dir: Path) -> float:
    """Try to read video duration from a sidecar if ffprobe result is unavailable."""
    dur_file = work_dir / "_video_duration.txt"
    if dur_file.is_file():
        try:
            return float(dur_file.read_text().strip())
        except Exception:
            pass
    return 0.0


# ---------------------------------------------------------------------------
# Stage 02b — Vocal separation and reference clip extraction
# ---------------------------------------------------------------------------

def stage_02b_separate_vocals(audio_wav: Path, work_dir: Path) -> tuple[Path, Path, Path]:
    _banner("02b", "Vocal/background separation (Demucs) + reference clip extraction")
    sys.path.insert(0, str(MODULE_DIR))
    from audio_processor import separate_vocals, extract_best_reference_clip

    vocals_wav, background_wav = separate_vocals(audio_wav, work_dir)

    clips_dir = work_dir / "voice_profile_clips"
    ref_clip = extract_best_reference_clip(vocals_wav, clips_dir, clip_duration_sec=10.0)

    # Also save a copy as voice_profile_reference.wav for compatibility with cloner.py
    ref_compat = work_dir / "voice_profile_reference.wav"
    if not ref_compat.is_file():
        shutil.copy2(str(ref_clip), str(ref_compat))

    print(f"[+] Vocals: {vocals_wav.name}")
    print(f"[+] Background: {background_wav.name}")
    print(f"[+] Reference clip: {ref_clip.name}")
    return vocals_wav, background_wav, clips_dir


# ---------------------------------------------------------------------------
# Stage 03 — Natural translation
# ---------------------------------------------------------------------------

def stage_03_translate(
    transcript_info: dict,
    target_lang: str,
    work_dir: Path,
) -> str:
    _banner("03", f"Natural idiomatic translation -> {target_lang}")
    sys.path.insert(0, str(MODULE_DIR))
    from translator import translate_for_dubbing

    full_text = transcript_info["full_text"]
    detected_lang = transcript_info["detected_lang"]
    speech_duration = transcript_info["speech_duration"]

    translated = translate_for_dubbing(
        text=full_text,
        source_lang=detected_lang,
        target_lang=target_lang,
        target_duration=speech_duration,
        work_dir=work_dir,
    )
    return translated


# ---------------------------------------------------------------------------
# Stage 04 — XTTS v2 voice cloning (with legacy cloner.py fallback)
# ---------------------------------------------------------------------------

def stage_04_synthesize_voice(
    translated_text: str,
    target_lang: str,
    vocals_wav: Path,
    clips_dir: Path,
    work_dir: Path,
    speech_duration: float,
) -> tuple[Path, Path]:
    _banner("04", "XTTS v2 voice cloning with duration-precise alignment")
    sys.path.insert(0, str(MODULE_DIR))

    # Try the new synthesizer first
    try:
        from voice_synthesizer import synthesize_dubbed_audio
        return synthesize_dubbed_audio(
            text=translated_text,
            target_lang=target_lang,
            vocals_path=vocals_wav,
            clips_dir=clips_dir,
            work_dir=work_dir,
            target_speech_duration=speech_duration,
        )
    except Exception as exc:
        print(f"[!] voice_synthesizer failed ({exc}), falling back to cloner.py ...")

    # Fallback: invoke cloner.py subprocess
    text_file = work_dir / "dubbed_text.txt"
    text_file.write_text(translated_text, encoding="utf-8")

    profile_json = work_dir / "voice_profile.json"
    if not profile_json.is_file():
        # Create minimal profile for cloner.py compatibility
        ref_wav = clips_dir / "clip_01.wav"
        if not ref_wav.is_file():
            ref_wav = vocals_wav
        _build_minimal_profile(profile_json, work_dir, ref_wav)

    ref_wav = work_dir / "voice_profile_reference.wav"
    if not ref_wav.is_file():
        ref_wav = clips_dir / "clip_01.wav"

    voice_only_wav = work_dir / "cloned_voice_only.wav"
    dubbed_mp3 = work_dir / "dubbed_audio.mp3"
    dubbed_wav = work_dir / "dubbed_audio.wav"

    cloner_script = MODULE_DIR / "cloner.py"
    cmd = [
        sys.executable, str(cloner_script),
        "--text-file", str(text_file),
        "--profile", str(profile_json),
        "--reference", str(ref_wav),
        "--clips-dir", str(clips_dir),
        "--voice-only-wav", str(voice_only_wav),
        "--output-mp3", str(dubbed_mp3),
        "--output-wav", str(dubbed_wav),
        "--language", target_lang,
    ]
    if speech_duration > 0.5:
        cmd.extend(["--target-duration", f"{speech_duration:.2f}"])

    res = subprocess.run(cmd, cwd=str(MODULE_DIR), capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        err = res.stderr or res.stdout
        raise RuntimeError(f"cloner.py failed: {err[-500:]}")

    return dubbed_wav, dubbed_mp3


def _build_minimal_profile(profile_json: Path, work_dir: Path, ref_wav: Path):
    """Write a minimal voice_profile.json so cloner.py can read it."""
    import librosa, json
    try:
        y, sr = librosa.load(str(ref_wav), sr=22050, mono=True)
        dur = len(y) / sr
    except Exception:
        dur = 0.0

    bg_wav = work_dir / "voice_profile_background.wav"
    profile = {
        "metadata": {"duration_sec": dur},
        "pitch": {"f0_hz_median": 150.0, "intonation_variability_semitone_std": 15.0},
        "timbre": {"mfcc_mean": [0.0] * 20},
        "energy_loudness": {"speech_loudness_db_mean": -20.0},
        "background": {
            "background_wav": str(bg_wav) if bg_wav.is_file() else "",
            "speech_start_sec": 0.0,
            "speech_duration_sec": dur,
            "duration_sec": dur,
            "voice_level_db_in_original": -20.0,
        },
        "files": {
            "background_wav": str(bg_wav) if bg_wav.is_file() else "",
        },
    }
    profile_json.write_text(json.dumps(profile, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Stage 05/06 — Mix voice with background + final audio creation
# ---------------------------------------------------------------------------

def stage_05_mix_with_background(
    voice_only_wav: Path,
    background_wav: Path,
    work_dir: Path,
    video_duration: float,
    speech_start_sec: float = 0.0,
) -> Path:
    _banner("05", "Mixing dubbed voice with original background")
    sys.path.insert(0, str(MODULE_DIR))
    from audio_processor import mix_voice_with_background
    import soundfile as sf

    y_voice, sr_voice = sf.read(str(voice_only_wav), dtype="float32")
    if y_voice.ndim > 1:
        y_voice = y_voice.mean(axis=1)  # mono

    mixed, out_sr = mix_voice_with_background(
        voice_y=y_voice,
        voice_sr=sr_voice,
        background_path=background_wav,
        video_duration=video_duration,
        speech_start_sec=speech_start_sec,
    )

    final_mix_wav = work_dir / "dubbed_audio.wav"
    # mixed is (2, N) stereo float32
    sf.write(str(final_mix_wav), mixed.T, out_sr)
    print(f"[+] Final mixed audio: {final_mix_wav.name} ({mixed.shape[1] / out_sr:.2f}s stereo)")

    # Also export MP3
    final_mix_mp3 = work_dir / "dubbed_audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(final_mix_wav), "-b:a", "192k", str(final_mix_mp3)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    return final_mix_mp3


# ---------------------------------------------------------------------------
# Stage 07 — Video remux
# ---------------------------------------------------------------------------

def stage_07_remux_video(video_path: Path, audio_path: Path, video_duration: float, work_dir: Path) -> Path:
    _banner("07", "Remuxing video with dubbed audio (FFmpeg)")
    output_video = work_dir / "final_dubbed_video.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
    ]
    if video_duration > 0:
        cmd += ["-t", f"{video_duration:.4f}"]
    cmd.append(str(output_video))

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg remux failed: {res.stderr[-400:]}")

    print(f"[+] Final dubbed video: {output_video.name} ({os.path.getsize(output_video)} bytes)")
    return output_video


# ---------------------------------------------------------------------------
# Full pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    video_path: Path,
    target_lang: str = "hi",
    work_dir: Path | None = None,
    source_lang: str = "auto",
) -> Path:
    _require_ffmpeg()
    start_time = time.time()

    if not video_path.is_file():
        sys.exit(f"[ERROR] Input video not found: {video_path}")

    if work_dir is None:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        work_dir = MODULE_DIR / "outputs" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 72)
    print(f"  NATIVOX NATURAL DUBBING PIPELINE")
    print(f"  Input  : {video_path.name}")
    print(f"  Target : {target_lang.upper()}")
    print(f"  Output : {work_dir}")
    print("=" * 72)

    # Stage 01
    audio_wav, audio_mp3, video_duration = stage_01_extract_audio(video_path, work_dir)
    # Persist video duration for fallback reads
    (work_dir / "_video_duration.txt").write_text(str(video_duration), encoding="utf-8")

    # Stage 02a
    transcript_info = stage_02a_transcribe(audio_wav, work_dir, source_lang)
    speech_start = transcript_info["speech_start"]
    speech_duration = transcript_info["speech_duration"]

    # Stage 02b
    vocals_wav, background_wav, clips_dir = stage_02b_separate_vocals(audio_wav, work_dir)

    # Stage 03
    translated_text = stage_03_translate(transcript_info, target_lang, work_dir)

    # Stage 04
    voice_wav, voice_mp3 = stage_04_synthesize_voice(
        translated_text, target_lang, vocals_wav, clips_dir, work_dir, speech_duration
    )

    # Stage 05 — mix voice with background
    # voice_wav produced by voice_synthesizer is voice-only; mix it with background
    voice_only_wav = work_dir / "cloned_voice_only.wav"
    if not voice_only_wav.is_file():
        # voice_synthesizer saved it as dubbed_audio.wav; treat it as voice_only
        voice_only_wav = voice_wav

    if background_wav.is_file():
        final_audio = stage_05_mix_with_background(
            voice_only_wav, background_wav, work_dir, video_duration, speech_start
        )
    else:
        final_audio = voice_mp3 if voice_mp3.is_file() else voice_wav

    # Stage 07 — remux
    final_video = stage_07_remux_video(video_path, final_audio, video_duration, work_dir)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 72}")
    print(f"  PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f"  Dubbed video : {final_video}")
    print(f"  All artifacts: {work_dir}")
    print("=" * 72 + "\n")

    return final_video


# ---------------------------------------------------------------------------
# Standalone stage functions kept for backward-compat with server.py
# ---------------------------------------------------------------------------

def check_ffmpeg():
    _require_ffmpeg()


def stage_01_extract_audio_compat(video_path: Path, work_dir: Path) -> tuple[Path, float]:
    """Compatibility wrapper returning (audio_mp3, duration) like old pipeline.py"""
    audio_wav, audio_mp3, video_duration = stage_01_extract_audio(video_path, work_dir)
    return audio_mp3, video_duration


def stage_02a_transcribe_compat(audio_path: Path, work_dir: Path) -> tuple[str, str, float, float]:
    """Returns (full_text, detected_lang, speech_start, speech_duration)"""
    info = stage_02a_transcribe(audio_path, work_dir)
    return info["full_text"], info["detected_lang"], info["speech_start"], info["speech_duration"]


def stage_02b_voice_profile(audio_path: Path, work_dir: Path) -> tuple[Path, Path, Path]:
    """Compatibility wrapper returning (profile_json, clips_dir, ref_wav)"""
    vocals_wav, background_wav, clips_dir = stage_02b_separate_vocals(audio_path, work_dir)
    # Build minimal voice_profile.json so old server code doesn't crash
    profile_json = work_dir / "voice_profile.json"
    ref_wav = work_dir / "voice_profile_reference.wav"
    if not profile_json.is_file():
        _build_minimal_profile(profile_json, work_dir, clips_dir / "clip_01.wav")
    return profile_json, clips_dir, ref_wav


def stage_translate(text: str, source_lang: str, target_lang: str, work_dir: Path, target_duration: float = None) -> str:
    """Compatibility wrapper for server.py"""
    from translator import translate_for_dubbing
    return translate_for_dubbing(text, source_lang, target_lang, target_duration, work_dir)


def stage_06_voice_clone(
    text_file: Path,
    profile_json: Path,
    clips_dir: Path,
    ref_wav: Path,
    work_dir: Path,
    target_lang: str,
    target_duration: float = None,
) -> Path:
    """Compatibility wrapper for server.py — returns final audio path"""
    text = text_file.read_text(encoding="utf-8").strip()
    vocals_wav = work_dir / "voice_profile_vocals.wav"
    if not vocals_wav.is_file():
        vocals_wav = ref_wav
    voice_wav, voice_mp3 = stage_04_synthesize_voice(
        text, target_lang, vocals_wav, clips_dir, work_dir,
        speech_duration=target_duration or 0.0,
    )

    # Mix with background
    bg_wav = work_dir / "voice_profile_background.wav"
    voice_only = work_dir / "cloned_voice_only.wav"
    if not voice_only.is_file():
        voice_only = voice_wav

    dur_file = work_dir / "_video_duration.txt"
    video_dur = float(dur_file.read_text().strip()) if dur_file.is_file() else (target_duration or 0.0)

    if bg_wav.is_file():
        try:
            return stage_05_mix_with_background(voice_only, bg_wav, work_dir, video_dur)
        except Exception as exc:
            print(f"[!] Background mix failed: {exc}")

    return voice_mp3 if voice_mp3.is_file() else voice_wav


def stage_07_merge_video(video_path: Path, audio_path: Path, video_dur: float, work_dir: Path) -> Path:
    """Compatibility wrapper for server.py"""
    return stage_07_remux_video(video_path, audio_path, video_dur, work_dir)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Nativox Dubbing_Babin - Natural Actor Voice Dubbing Pipeline"
    )
    parser.add_argument("--video", "-v", required=True, help="Path to input video (.mp4)")
    parser.add_argument(
        "--target-lang", "-l", default="hi",
        help="Target language code: hi, bn, en, es, fr, de, ja, ru, ko, zh-cn, it, pt, pl, tr, nl, cs, ar, hu"
    )
    parser.add_argument("--source-lang", "-s", default="auto", help="Source language code (default: auto-detect)")
    parser.add_argument("--work-dir", "-o", default=None, help="Custom output directory")
    args = parser.parse_args()

    video = Path(args.video).resolve()
    work = Path(args.work_dir).resolve() if args.work_dir else None
    run_pipeline(video, target_lang=args.target_lang, work_dir=work, source_lang=args.source_lang)


if __name__ == "__main__":
    main()
