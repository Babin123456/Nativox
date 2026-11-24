#!/usr/bin/env python3
"""
Nativox Dubbing_Babin - Web Server and REST API
================================================
Provides a FastAPI web dashboard to run the natural dubbing pipeline.

Run:
    cd Dubbing_Babin
    python server.py
    # or
    python server.py --port 8080
"""

import argparse
import os
import shutil
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

MODULE_DIR = Path(__file__).resolve().parent
WEB_DIR = MODULE_DIR / "web"
OUTPUTS_DIR = MODULE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MODULE_DIR))
import pipeline

app = FastAPI(title="Nativox Dubbing_Babin API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: Dict[str, Dict[str, Any]] = {}

SUPPORTED_LANGS = {
    "hi": "Hindi",
    "bn": "Bengali",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "tr": "Turkish",
    "nl": "Dutch",
    "cs": "Czech",
    "ar": "Arabic",
    "hu": "Hungarian",
    "zh-cn": "Chinese (Mandarin)",
}

TOTAL_STEPS = 7


def _log(job: dict, msg: str):
    job["logs"].append(msg)
    print(f"[{job['job_id']}] {msg}")


def run_pipeline_thread(job_id: str, video_path: Path, target_lang: str):
    job = JOBS[job_id]
    work_dir = OUTPUTS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    job["work_dir"] = str(work_dir)

    try:
        pipeline.check_ffmpeg()
        start = time.time()

        # Stage 01
        job["current_step"] = 1
        _log(job, "Stage 01: Demuxing audio track from video...")
        audio_wav, audio_mp3, video_duration = pipeline.stage_01_extract_audio(video_path, work_dir)
        (work_dir / "_video_duration.txt").write_text(str(video_duration), encoding="utf-8")
        _log(job, f"Stage 01: Audio demuxed ({video_duration:.2f}s)")

        # Stage 02a
        job["current_step"] = 2
        _log(job, "Stage 02a: Transcribing speech with faster-whisper...")
        transcript_info = pipeline.stage_02a_transcribe(audio_wav, work_dir)
        full_text = transcript_info["full_text"]
        detected_lang = transcript_info["detected_lang"]
        speech_start = transcript_info["speech_start"]
        speech_duration = transcript_info["speech_duration"]
        _log(job, f"Stage 02a: Transcribed ({detected_lang}, {len(full_text.split())} words, speech window {speech_duration:.2f}s)")
        _log(job, f"Stage 02a: Transcript: \"{full_text[:80]}{'...' if len(full_text) > 80 else ''}\"")

        # Stage 02b
        job["current_step"] = 3
        _log(job, "Stage 02b: Separating vocals from background (Demucs)...")
        vocals_wav, background_wav, clips_dir = pipeline.stage_02b_separate_vocals(audio_wav, work_dir)
        _log(job, "Stage 02b: Vocal/background separation complete")

        # Stage 03
        job["current_step"] = 4
        _log(job, f"Stage 03: Translating to {SUPPORTED_LANGS.get(target_lang, target_lang)}...")
        translated_text = pipeline.stage_03_translate(transcript_info, target_lang, work_dir)
        _log(job, f"Stage 03: Translated: \"{translated_text[:80]}{'...' if len(translated_text) > 80 else ''}\"")

        # Stage 04
        job["current_step"] = 5
        _log(job, f"Stage 04: Synthesizing voice with XTTS v2 (target: {speech_duration:.2f}s)...")
        voice_wav, voice_mp3 = pipeline.stage_04_synthesize_voice(
            translated_text, target_lang, vocals_wav, clips_dir, work_dir, speech_duration
        )
        _log(job, "Stage 04: Voice synthesis and duration alignment complete")

        # Stage 05
        job["current_step"] = 6
        _log(job, "Stage 05: Mixing dubbed voice with original background...")
        voice_only_wav = work_dir / "cloned_voice_only.wav"
        if not voice_only_wav.is_file():
            voice_only_wav = voice_wav
        if background_wav.is_file():
            final_audio = pipeline.stage_05_mix_with_background(
                voice_only_wav, background_wav, work_dir, video_duration, speech_start
            )
        else:
            final_audio = voice_mp3 if voice_mp3.is_file() else voice_wav
        _log(job, "Stage 05: Audio mix complete (voice + background)")

        # Stage 07
        job["current_step"] = 7
        _log(job, "Stage 07: Remuxing video with dubbed audio...")
        final_video = pipeline.stage_07_remux_video(video_path, final_audio, video_duration, work_dir)
        _log(job, f"Stage 07: Final dubbed video ready: {final_video.name}")

        elapsed = time.time() - start
        _log(job, f"Pipeline finished in {elapsed:.1f}s")
        job["status"] = "completed"
        job["output_video"] = str(final_video)

    except Exception as exc:
        import traceback
        job["status"] = "failed"
        job["error"] = str(exc)
        _log(job, f"[ERROR] Pipeline failed: {exc}")
        _log(job, traceback.format_exc()[-600:])


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = WEB_DIR / "index.html"
    if not html_file.is_file():
        raise HTTPException(status_code=404, detail="Web UI not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/languages")
def get_languages():
    return {"languages": SUPPORTED_LANGS}


@app.post("/api/dub")
async def start_dubbing(video: UploadFile = File(...), target_lang: str = Form("hi")):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    work_dir = OUTPUTS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    input_video_path = work_dir / f"input_{video.filename}"
    with input_video_path.open("wb") as buf:
        shutil.copyfileobj(video.file, buf)

    JOBS[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "current_step": 0,
        "total_steps": TOTAL_STEPS,
        "target_lang": target_lang,
        "target_lang_name": SUPPORTED_LANGS.get(target_lang, target_lang),
        "logs": [f"Job {job_id} registered. Video uploaded: {video.filename}"],
        "created_at": time.time(),
        "output_video": None,
        "error": None,
        "work_dir": None,
    }

    threading.Thread(
        target=run_pipeline_thread,
        args=(job_id, input_video_path, target_lang),
        daemon=True,
    ).start()

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(JOBS[job_id])


@app.get("/api/video/{job_id}")
def download_video(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOBS[job_id]
    if job.get("status") != "completed" or not job.get("output_video"):
        raise HTTPException(status_code=400, detail="Video not ready yet")
    video_path = Path(job["output_video"])
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Output video file missing")
    return FileResponse(str(video_path), media_type="video/mp4", filename=video_path.name)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)


def _silence_proactor():
    """Suppress harmless WinError 10054 on Windows video seeks."""
    if sys.platform == "win32":
        from asyncio.proactor_events import _ProactorBasePipeTransport
        orig = _ProactorBasePipeTransport._call_connection_lost

        def _patched(self, exc):
            try:
                orig(self, exc)
            except (ConnectionResetError, OSError):
                pass

        _ProactorBasePipeTransport._call_connection_lost = _patched


_silence_proactor()


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="Nativox Dubbing_Babin Web Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  NATIVOX DUBBING_BABIN - NATURAL VOICE DUBBING STUDIO")
    print(f"  Web Dashboard: http://{args.host}:{args.port}")
    print("=" * 65 + "\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
