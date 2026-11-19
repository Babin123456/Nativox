#!/usr/bin/env python3
"""
Nativox Dubbing_Babin - Web Server & Pipeline Runner
===================================================
Provides a modern FastAPI/Starlette web dashboard and REST API
to run the streamlined [1, 2a, 2b, Translate, 6, 7] pipeline.

Run Command:
    cd Dubbing_Babin
    python server.py
    (or: python server.py --port 8080)
"""

import argparse
import asyncio
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
from fastapi.staticfiles import StaticFiles

# Setup directory references
MODULE_DIR = Path(__file__).resolve().parent
ROOT_DIR = MODULE_DIR.parent
WEB_DIR = MODULE_DIR / "web"
OUTPUTS_DIR = MODULE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Import pipeline runner
sys.path.insert(0, str(MODULE_DIR))
import pipeline

app = FastAPI(title="Nativox Dubbing_Babin API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking
JOBS: Dict[str, Dict[str, Any]] = {}


def run_pipeline_thread(job_id: str, video_path: Path, target_lang: str):
    job = JOBS[job_id]
    work_dir = OUTPUTS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    job["work_dir"] = str(work_dir)

    def log(msg: str):
        job["logs"].append(msg)
        print(f"[{job_id}] {msg}")

    try:
        pipeline.check_ffmpeg()
        start_time = time.time()
        log(f"Starting Dubbing_Babin pipeline for {video_path.name}")
        log(f"Target language: {target_lang}")

        # Stage 1: Demuxing
        job["current_step"] = 1
        log("Stage 01: Demuxing video audio track with FFmpeg...")
        audio_path, video_duration = pipeline.stage_01_extract_audio(video_path, work_dir)
        log(f"Stage 01: Audio extracted ({os.path.getsize(audio_path)} bytes), duration: {video_duration:.2f}s")

        # Stage 2: Parallel Transcription & Profiling
        job["current_step"] = 2
        log("Stage 02a: Transcribing speech with Faster-Whisper neural model...")
        transcript, detected_lang = pipeline.stage_02a_transcribe(audio_path, work_dir)
        log(f"Stage 02a: Transcription completed ({detected_lang}, {len(transcript.split())} words)")

        log("Stage 02b: Extracting speaker acoustic profile & clean reference clips (Demucs)...")
        profile_json, clips_dir, ref_wav = pipeline.stage_02b_voice_profile(audio_path, work_dir)
        log("Stage 02b: Speaker acoustic profile and clean reference clips extracted")

        # Stage 3: Direct Translation
        job["current_step"] = 3
        log(f"Translation: Translating speech directly to {target_lang}...")
        dubbed_text = pipeline.stage_translate(transcript, detected_lang, target_lang, work_dir)
        dubbed_text_file = work_dir / "dubbed_text.txt"
        log(f"Translation: Speech translated to {target_lang}: '{dubbed_text[:60]}...'")

        # Stage 6: Voice Cloning via Stage 08
        job["current_step"] = 4
        log("Stage 06: Synthesizing speech with author's cloned voice (XTTS v2)...")
        dubbed_audio = pipeline.stage_06_voice_clone(
            dubbed_text_file, profile_json, clips_dir, ref_wav, work_dir, target_lang
        )
        log("Stage 06: Cloned speech audio synthesized with background audio preserved")

        # Stage 7: Remuxing
        job["current_step"] = 5
        log("Stage 07: Remuxing original video with dubbed audio track...")
        final_video = pipeline.stage_07_merge_video(video_path, dubbed_audio, video_duration, work_dir)
        log(f"Stage 07: Final dubbed video remuxed successfully: {final_video.name}")

        elapsed = time.time() - start_time
        log(f"Pipeline finished in {elapsed:.1f} seconds! Output ready.")
        job["status"] = "completed"
        job["output_video"] = str(final_video)
        job["current_step"] = 6
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
        log(f"[ERROR] Pipeline failed: {exc}")


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = WEB_DIR / "index.html"
    if not html_file.is_file():
        raise HTTPException(status_code=404, detail="Web UI not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/dub")
async def start_dubbing(video: UploadFile = File(...), target_lang: str = Form("hi")):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    work_dir = OUTPUTS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    input_video_path = work_dir / f"input_{video.filename}"
    with input_video_path.open("wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    JOBS[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "current_step": 0,
        "target_lang": target_lang,
        "logs": [f"Job {job_id} registered. Video uploaded."],
        "created_at": time.time(),
        "output_video": None,
        "error": None
    }

    thread = threading.Thread(
        target=run_pipeline_thread,
        args=(job_id, input_video_path, target_lang),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(JOBS[job_id])


@app.get("/api/video/{job_id}")
def get_output_video(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOBS[job_id]
    if job.get("status") != "completed" or not job.get("output_video"):
        raise HTTPException(status_code=400, detail="Video is not ready yet")
    
    video_path = Path(job["output_video"])
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Output video file missing")
    return FileResponse(str(video_path), media_type="video/mp4", filename=video_path.name)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return JSONResponse(status_code=204, content={})


def silence_proactor_reset():
    """Silences harmless WinError 10054 on Windows when browsers seek video."""
    if sys.platform == "win32":
        from asyncio.proactor_events import _ProactorBasePipeTransport
        orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost

        def _patched_call_connection_lost(self, exc):
            try:
                orig_call_connection_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass

        _ProactorBasePipeTransport._call_connection_lost = _patched_call_connection_lost


silence_proactor_reset()


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="Nativox Dubbing_Babin Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to run web server on")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print(f"  NATIVOX DUBBING_BABIN - STREAMLINED WEB STUDIO")
    print(f"  Active Stages: [1, 2a, 2b, Direct Translation, 6, 7]")
    print(f"  Web Dashboard: http://{args.host}:{args.port}")
    print("=" * 65 + "\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
