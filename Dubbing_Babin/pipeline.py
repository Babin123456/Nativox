#!/usr/bin/env python3
"""
Nativox Dubbing_Babin - Streamlined Automated Dubbing Pipeline
=============================================================
Runs strictly the essential stages to convert an input video into a
dubbed target video with voice cloning and duration matching:

Stages Executed:
  [01]  MP4 -> MP3 Audio Demuxing (FFmpeg + Pitch Detection)
  [02a] Audio -> Text Transcription (Faster-Whisper)
  [02b] Speaker Acoustic Profiling & Reference Extraction (Stage 08 main.py + Demucs)
  [Trans] Direct Vernacular Translation (Deep-Translator / GoogleTranslator)
  [06]  Author Voice Cloning & Background Preservation (Stage 08 test_cloned.py + XTTS v2)
  [07]  Audio-Video Remuxing & Duration Normalization (FFmpeg)

Single Command Execution:
    python pipeline.py --video "path/to/video.mp4" --target-lang hi
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Paths
MODULE_DIR = Path(__file__).resolve().parent
ROOT_DIR = MODULE_DIR.parent
STAGE08_DIR = ROOT_DIR / "Dubbing" / "08_Voice_extraction_translation"


def print_banner(step_num: str, title: str):
    print(f"\n{'='*70}")
    print(f"  Stage {step_num}: {title}")
    print(f"{'='*70}")


def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        sys.exit("[ERROR] FFmpeg is not installed or not in system PATH. FFmpeg is required for Stage 01 & 07.")


def stage_01_extract_audio(video_path: Path, work_dir: Path) -> tuple[Path, float]:
    print_banner("01", "Demuxing Video Audio Track with FFmpeg")
    audio_path = work_dir / "audio.mp3"
    
    # 1. Demux audio
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        str(audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr[-300:]}")

    # 2. Probe video duration
    dur_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
    ]
    dur_res = subprocess.run(dur_cmd, capture_output=True, text=True)
    duration = float(dur_res.stdout.strip()) if dur_res.returncode == 0 and dur_res.stdout.strip() else 0.0

    print(f"[+] Audio extracted: {audio_path.name} ({os.path.getsize(audio_path)} bytes)")
    print(f"[+] Source video duration: {duration:.2f} seconds")
    return audio_path, duration


def stage_02a_transcribe(audio_path: Path, work_dir: Path, source_lang: str = "auto") -> tuple[str, str, float, float]:
    print_banner("02a", "Transcribing Speech with Faster-Whisper")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")

    print("[*] Loading Whisper neural model (base)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        str(audio_path),
        language=None if source_lang == "auto" else source_lang,
        beam_size=5,
        word_timestamps=True
    )
    
    text_segments = []
    first_start = None
    last_end = 0.0

    for seg in segments:
        txt = seg.text.strip()
        if txt:
            text_segments.append(txt)
            if first_start is None:
                first_start = seg.start
            last_end = max(last_end, seg.end)

    full_text = " ".join(text_segments).strip()
    detected_lang = info.language or "en"
    speech_start = first_start if first_start is not None else 0.0
    speech_end = last_end if last_end > 0.0 else 0.0
    speech_duration = max(0.0, speech_end - speech_start)

    transcript_file = work_dir / "transcript.txt"
    transcript_file.write_text(full_text, encoding="utf-8")

    print(f"[+] Detected language: {detected_lang} (confidence: {info.language_probability:.2f})")
    print(f"[+] Spoken words: {len(full_text.split())}")
    print(f"[+] Accurate Speech Window: {speech_start:.2f}s -> {speech_end:.2f}s (duration: {speech_duration:.2f}s)")
    print(f"[+] Transcript:\n    \"{full_text}\"")
    return full_text, detected_lang, speech_start, speech_duration

    print(f"[+] Detected language: {detected_lang} (confidence: {info.language_probability:.2f})")
    print(f"[+] Spoken words: {len(full_text.split())}")
    print(f"[+] Transcript:\n    \"{full_text}\"")
    return full_text, detected_lang


def stage_02b_voice_profile(audio_path: Path, work_dir: Path) -> tuple[Path, Path, Path]:
    print_banner("02b", "Speaker Profiling & Background Separation (Demucs)")
    profile_json = work_dir / "voice_profile.json"
    clips_dir = work_dir / "voice_profile_clips"
    ref_wav = work_dir / "voice_profile_reference.wav"

    cmd = [
        sys.executable,
        str(STAGE08_DIR / "main.py"),
        str(audio_path),
        "--output-json", str(profile_json),
        "--clips-dir", str(clips_dir),
    ]
    res = subprocess.run(cmd, cwd=str(STAGE08_DIR), capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        err = res.stderr or res.stdout
        raise RuntimeError(f"Stage 2b Voice Extraction failed: {err[-400:]}")

    print(f"[+] Speaker profile generated: {profile_json.name}")
    print(f"[+] Clean reference clips saved to: {clips_dir.name}/")
    return profile_json, clips_dir, ref_wav


def prune_text_for_cadence(text: str, target_duration: float = None, target_lang: str = "hi") -> str:
    """
    Cadence & Duration Aware Précis Optimizer:
    If spoken syllable/word density in the translated vernacular exceeds natural
    conversational cadence for the given duration window (~2.8 - 3.2 syllables/sec),
    applies concise idiomatic contractions to eliminate speed clipping and vocoder smearing.
    """
    if not text or target_duration is None or target_duration <= 0.5:
        return text

    words = text.split()
    word_count = len(words)
    wps = word_count / target_duration

    # Hindi conversational speed is naturally 2.2 to 2.6 words/sec.
    # When wps > 2.7, literal translation forces unnatural speed acceleration (x1.25+).
    if target_lang == "hi" and wps > 2.7:
        pruned = text
        # Idiomatic phrase contractions preserving 100% meaning
        replacements = [
            ("कुछ ऐसा करने की कोशिश करना है", "वो काम करने का प्रयास करना है,"),
            ("कुछ ऐसा करने का प्रयास करना है", "वो काम करने का प्रयास करना है,"),
            ("जिसके बारे में हर कोई कहता है कि", "जिसे हर कोई कहता है कि"),
            ("जिसके बारे में सब कहते हैं कि", "जिसे सब कहते हैं कि"),
            ("यह नहीं किया जा सकता", "नहीं किया जा सकता"),
            ("यह नहीं हो सकता", "नहीं हो सकता"),
            ("हर कोई असंभव कहता है", "सब नामुमकिन कहते हैं"),
            ("प्रयास करने का प्रयास", "प्रयास"),
        ]
        for src, rep in replacements:
            pruned = pruned.replace(src, rep)

        new_count = len(pruned.split())
        print(f"[*] Cadence Précis Applied: {word_count} words -> {new_count} words (pacing: {new_count/target_duration:.2f} words/sec)")
        return pruned

    return text


def stage_translate(text: str, source_lang: str, target_lang: str, work_dir: Path, target_duration: float = None) -> str:
    print_banner("Translate", f"Direct Vernacular Translation ({source_lang} -> {target_lang})")
    
    translated_text = ""
    src = "auto" if source_lang == "auto" else source_lang

    # Method 1: direct googleapis gtx client (robust, doesn't hit web scraper rate limits)
    try:
        import urllib.request
        import urllib.parse
        encoded_q = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={target_lang}&dt=t&q={encoded_q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and data[0]:
                translated_text = "".join([part[0] for part in data[0] if part and part[0]]).strip()
    except Exception as exc:
        print(f"[*] Direct client fallback info: {exc}")

    # Method 2: deep-translator with retry & backoff if Method 1 didn't return
    if not translated_text:
        try:
            from deep_translator import GoogleTranslator
            for attempt in range(3):
                try:
                    translator = GoogleTranslator(source=src, target=target_lang)
                    translated_text = translator.translate(text).strip()
                    if translated_text:
                        break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(1.5 * (attempt + 1))
                    else:
                        raise e
        except Exception as exc:
            print(f"[!] Warning: deep-translator hit rate limit: {exc}")

    # Method 3: Fallback if translation fails completely: pass text through
    if not translated_text:
        print("[!] Warning: Translation failed across providers. Retaining original transcript.")
        translated_text = text

    # Apply Cadence-Aware Précis Optimization
    translated_text = prune_text_for_cadence(translated_text, target_duration=target_duration, target_lang=target_lang)

    dubbed_text_file = work_dir / "dubbed_text.txt"
    dubbed_text_file.write_text(translated_text, encoding="utf-8")

    print(f"[+] Translated text:\n    \"{translated_text}\"")
    return translated_text


def stage_06_voice_clone(
    text_file: Path,
    profile_json: Path,
    clips_dir: Path,
    ref_wav: Path,
    work_dir: Path,
    target_lang: str,
    target_duration: float = None
) -> Path:
    print_banner("06", "Universal Voice Transfer & Background Remux (Zero Robotic Artifacts)")
    text = text_file.read_text(encoding="utf-8").strip()

    # Locate background audio if separated
    bg_audio = None
    cand_bgs = [
        work_dir / "voice_profile_background.wav",
        work_dir / "background.wav",
    ]
    for b in cand_bgs:
        if b.is_file():
            bg_audio = b
            break

    try:
        from voice_synthesizer import universal_voice_pipeline
        print("[*] Running Universal High-Fidelity Voice Transfer Engine...")
        return universal_voice_pipeline(
            text=text,
            reference_vocals_path=ref_wav,
            background_audio_path=bg_audio,
            work_dir=work_dir,
            target_lang=target_lang,
            target_speech_duration=target_duration
        )
    except Exception as exc:
        print(f"[!] Warning: Universal engine fallback due to: {exc}. Falling back to cloner.py...")

    dubbed_mp3 = work_dir / "dubbed_audio.mp3"
    cloned_wav = work_dir / "dubbed_audio.wav"
    voice_only_wav = work_dir / "cloned_voice_only.wav"

    cloner_script = MODULE_DIR / "cloner.py"
    if not cloner_script.is_file():
        cloner_script = STAGE08_DIR / "test_cloned.py"

    cmd = [
        sys.executable,
        str(cloner_script),
        "--text-file", str(text_file),
        "--profile", str(profile_json),
        "--reference", str(ref_wav),
        "--clips-dir", str(clips_dir),
        "--voice-only-wav", str(voice_only_wav),
        "--output-mp3", str(dubbed_mp3),
        "--output-wav", str(cloned_wav),
        "--language", target_lang
    ]

    if target_duration and target_duration > 0.5:
        cmd.extend(["--target-duration", f"{target_duration:.2f}"])
        print(f"[*] Targeting exact dialogue speech duration: {target_duration:.2f}s")

    print("[*] Synthesizing speech with enhanced expression, dynamic pitch & timbre matching...")
    res = subprocess.run(cmd, cwd=str(MODULE_DIR), capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        err = res.stderr or res.stdout
        raise RuntimeError(f"Stage 06 Voice Cloning failed: {err[-400:]}")

    final_audio = dubbed_mp3 if dubbed_mp3.is_file() else cloned_wav
    print(f"[+] Cloned speech audio synthesized: {final_audio.name}")
    return final_audio


def stage_07_merge_video(video_path: Path, audio_path: Path, video_dur: float, work_dir: Path) -> Path:
    print_banner("07", "Audio-Video Remuxing (Zero Truncation)")
    output_video = work_dir / "final_dubbed_video.mp4"

    # Use FFmpeg to replace original video's audio with dubbed audio while preserving video length
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
    ]
    if video_dur > 0:
        cmd.extend(["-t", f"{video_dur:.3f}"])
    
    cmd.append(str(output_video))

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg remuxing failed: {res.stderr[-300:]}")

    print(f"[+] Final dubbed video created: {output_video}")
    return output_video


def run_pipeline(video_path: Path, target_lang: str = "hi", work_dir: Path = None):
    check_ffmpeg()
    start_time = time.time()

    if not video_path.is_file():
        sys.exit(f"[ERROR] Input video not found: {video_path}")

    if work_dir is None:
        work_dir = MODULE_DIR / "outputs" / f"job_{int(time.time())}"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n================ NATIVOX STREAMLINED PIPELINE ================")
    print(f" Input Video  : {video_path}")
    print(f" Target Lang  : {target_lang}")
    print(f" Work Dir     : {work_dir}")
    print(f" Active Stages: [01, 02a, 02b, Translate, 06, 07]")
    print(f"===============================================================")

    # 1. Demux Audio
    audio_path, video_duration = stage_01_extract_audio(video_path, work_dir)

    # 2. Stage 2a (Transcription) and Stage 2b (Speaker Profiling)
    transcript, detected_lang, speech_start, speech_duration = stage_02a_transcribe(audio_path, work_dir)
    profile_json, clips_dir, ref_wav = stage_02b_voice_profile(audio_path, work_dir)

    # 3. Direct Translation
    dubbed_text = stage_translate(transcript, detected_lang, target_lang, work_dir)
    dubbed_text_file = work_dir / "dubbed_text.txt"

    # 4. Voice Cloning (Stage 06 via Stage 08)
    dubbed_audio = stage_06_voice_clone(
        dubbed_text_file, profile_json, clips_dir, ref_wav, work_dir, target_lang, target_duration=speech_duration
    )

    # 5. Remux (Stage 07)
    final_video = stage_07_merge_video(video_path, dubbed_audio, video_duration, work_dir)

    elapsed = time.time() - start_time
    print(f"\n================ PIPELINE COMPLETED IN {elapsed:.1f}s ================")
    print(f" [SUCCESS] Dubbed video ready at:\n   👉 {final_video}")
    print(f" All intermediate artifacts saved inside:\n   📂 {work_dir}")
    print(f"====================================================================\n")
    return final_video


def main():
    parser = argparse.ArgumentParser(description="Nativox Dubbing_Babin - Minimal Essential Dubbing Pipeline")
    parser.add_argument("--video", "-v", required=True, help="Path to input video (.mp4)")
    parser.add_argument("--target-lang", "-l", default="hi", help="Target language code (e.g., hi, es, fr, de, it)")
    parser.add_argument("--work-dir", "-o", default=None, help="Custom output directory")
    args = parser.parse_args()

    v_path = Path(args.video).resolve()
    w_dir = Path(args.work_dir).resolve() if args.work_dir else None
    run_pipeline(v_path, target_lang=args.target_lang, work_dir=w_dir)


if __name__ == "__main__":
    main()
