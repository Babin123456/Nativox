"""
app.py - Unified Nativox Studio: Stage 00 Auto Dubbing + Selective LipSync.

Architecture:
1. Receives input video.
2. Executes 00_Auto_Pip Stage 00 Dubbing directly (Voice extraction, Whisper transcription,
   Keyword extraction, Sentence construction, Reformation & Hindi Translation,
   Author voice cloning via XTTS v2 with duration alignment & timbre EQ, and Remuxing).
   -> Exactly replicates 00_Auto_Pip's output: final_dubbed_video.mp4 & dubbed_audio.wav.
3. Automatically chains Stage 2: Selective Sub-Nasal Lip-Sync (Wav2Lip GAN + MediaPipe 468 FaceMesh)
   -> Takes input_video.mp4 and dubbed_audio.wav, articulates lips on the translated dialogue,
      and blends back onto the original frame with 100% untouched upper face and background.
4. Saves final video into outputs/ and displays comparison in Web UI.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = BASE_DIR.parent
DUBBING_DIR = WORKSPACE_ROOT / "Dubbing" / "00_Auto_Pip"
LIPSYNC_DIR = WORKSPACE_ROOT / "LipSync_Babin"
LOCAL_JOBS_DIR = BASE_DIR / "jobs"
FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUTS_DIR = BASE_DIR / "outputs"

LOCAL_JOBS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Add 00_Auto_Pip and its parent to path so we can import directly
if str(DUBBING_DIR) not in sys.path:
    sys.path.insert(0, str(DUBBING_DIR))

import main as auto_pip_main

app = FastAPI(
    title="Nativox Universal Studio (Stage 00 Dubbing + LipSync)",
    description="Exact 00_Auto_Pip pipeline execution augmented with selective sub-nasal lip synchronization",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

job_registry: Dict[str, Dict[str, Any]] = {}


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    index_html = FRONTEND_DIR / "index.html"
    if index_html.exists():
        return HTMLResponse(content=index_html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Nativox Studio Online</h1>")


def _log(job_id: str, message: str):
    print(f"[{job_id}] {message}", flush=True)
    if job_id in job_registry:
        job_registry[job_id]["logs"] += message + "\n"


def _get_video_duration(video_path: Path) -> float:
    """Probes video duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return 0.0


def _run_unified_studio_pipeline(job_id: str, input_video_path: Path, job_dir: Path):
    """
    1. Executes the exact 00_Auto_Pip worker.
    2. Takes the dubbed audio and input video and performs selective lip-sync.
    """
    start_time = time.time()
    job_registry[job_id]["state"] = "running"
    job_registry[job_id]["start_time"] = start_time
    
    # Calculate tentative estimated duration based on video duration
    video_dur = _get_video_duration(input_video_path)
    job_registry[job_id]["video_duration"] = round(video_dur, 2)
    
    # CPU processing multiplier rule of thumb:
    # Stage 00 Dubbing (Whisper, Demucs/profiling, XTTS v2, T5): ~30s base overhead + ~3.5x video duration
    # Stage 2 Selective Lip-Sync (Wav2Lip face detection & inpainting): ~15s base overhead + ~4.5x video duration
    # Total tentative estimated duration (seconds):
    if video_dur > 0:
        tentative_seconds = round(45.0 + (video_dur * 8.0))
    else:
        tentative_seconds = 120.0
    job_registry[job_id]["estimated_duration"] = tentative_seconds

    _log(job_id, f"=== Starting Stage 00 Dubbing + Selective LipSync for {input_video_path.name} ===")
    if video_dur > 0:
        mins = int(tentative_seconds // 60)
        secs = int(tentative_seconds % 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        _log(job_id, f"[*] Video duration: {video_dur:.2f}s | Tentative estimated time: ~{time_str} ({tentative_seconds}s)")


    # -----------------------------------------------------------------
    # STEP 1: Run Stage 00 Auto Dubbing (Exact 00_Auto_Pip workflow)
    # -----------------------------------------------------------------
    _log(job_id, "\n[Stage 1/2] Executing Stage 00 Auto Dubbing Pipeline...")
    import orchestrator

    root_dir = DUBBING_DIR.parent
    _log(job_id, "  Ensuring Stage 00 microservices (ports 8001-8007) are running...")
    owned_processes = orchestrator.start_services(root_dir)

    auto_pip_main.job_store[job_id] = {
        "job_id": job_id,
        "filename": input_video_path.name,
        "status": "pending",
        "progress": 0,
        "current_step": 0,
        "step_name": "Initializing",
        "logs": [],
        "created_at": time.time(),
        "final_video_available": False,
        "requested_voice_gender": "auto",
        "requested_voice": None,
        "target_language": "hindi",
    }

    try:
        # Run 00_Auto_Pip worker synchronously in this thread
        auto_pip_main._run_job_worker(
            job_id=job_id,
            input_video_path=input_video_path,
            work_dir=job_dir,
            voice_gender="auto",
            custom_voice=None,
            target_language="hindi",
        )

        job_info = auto_pip_main.job_store.get(job_id, {})
        for log_line in job_info.get("logs", []):
            _log(job_id, f"  {log_line}")

        if job_info.get("status") == "failed":
            raise RuntimeError(job_info.get("error", "Stage 00 Dubbing failed"))

        # Verify Stage 00 generated products
        dubbed_video_path = job_dir / "final_dubbed_video.mp4"
        dubbed_audio_path = job_dir / "dubbed_audio.wav"
        if not dubbed_audio_path.exists():
            dubbed_audio_path = job_dir / "dubbed_audio.mp3"

        if not dubbed_audio_path.exists() or not dubbed_video_path.exists():
            raise FileNotFoundError(f"Stage 00 outputs missing in {job_dir}")

        _log(job_id, f"[Stage 1/2] Stage 00 Dubbing complete! (Audio: {dubbed_audio_path.name}, Video: {dubbed_video_path.name})")
        job_registry[job_id]["dubbed_video_url"] = f"/api/video/{job_id}/dubbed"

    except Exception as exc:
        job_registry[job_id]["state"] = "failed"
        job_registry[job_id]["elapsed_seconds"] = round(time.time() - start_time, 1)
        _log(job_id, f"[ERROR in Stage 00 Dubbing]: {str(exc)}")
        return

    # -----------------------------------------------------------------
    # STEP 2: Run Selective Sub-Nasal Lip-Syncing
    # -----------------------------------------------------------------
    _log(job_id, "\n[Stage 2/2] Adding Selective Sub-Nasal Lip-Syncing (Wav2Lip + MediaPipe)...")
    final_output_video = job_dir / "final_lipsynced_video.mp4"
    lipsync_script = BASE_DIR / "run_dub_lipsync.py"
    lipsync_py = str(LIPSYNC_DIR / ".venv" / "Scripts" / "python.exe")
    if not Path(lipsync_py).exists():
        lipsync_py = sys.executable

    cmd_lip = [
        lipsync_py,
        str(lipsync_script),
        "--video",
        str(input_video_path),
        "--audio",
        str(dubbed_audio_path),
        "--output",
        str(final_output_video),
    ]

    try:
        proc_lip = subprocess.Popen(
            cmd_lip,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(BASE_DIR),
        )

        for line in iter(proc_lip.stdout.readline, ""):
            _log(job_id, f"  {line.rstrip()}")

        proc_lip.wait()
        if proc_lip.returncode != 0:
            raise RuntimeError(f"run_dub_lipsync.py exited with code {proc_lip.returncode}")

        if not final_output_video.exists():
            raise FileNotFoundError("Final lip-synced video was not produced.")

        # Copy final lip-synced video to outputs/
        final_dest = OUTPUTS_DIR / f"{job_id}_final_lipsynced_video.mp4"
        shutil.copy2(final_output_video, final_dest)

        elapsed_total = round(time.time() - start_time, 1)
        mins = int(elapsed_total // 60)
        secs = int(elapsed_total % 60)
        time_taken_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        job_registry[job_id]["state"] = "completed"
        job_registry[job_id]["output_path"] = str(final_dest)
        job_registry[job_id]["output_video_url"] = f"/api/video/{job_id}/output"
        job_registry[job_id]["original_video_url"] = f"/api/video/{job_id}/original"
        job_registry[job_id]["elapsed_seconds"] = elapsed_total
        _log(job_id, f"\n=== SUCCESS! Dubbed + Lip-Synced video saved in outputs/: {final_dest.name} (Total time: {time_taken_str}) ===")

    except Exception as exc:
        job_registry[job_id]["state"] = "failed"
        job_registry[job_id]["elapsed_seconds"] = round(time.time() - start_time, 1)
        _log(job_id, f"[ERROR in Stage 2 LipSync]: {str(exc)}")


@app.post("/api/process")
async def process_video(
    video_file: Optional[UploadFile] = File(None),
    existing_video_path: Optional[str] = Form(None),
):
    """
    Accepts ONLY an input video.
    Executes Stage 00 Auto Dubbing + Selective Lip-Sync end-to-end.
    """
    new_job_id = f"job_{uuid.uuid4().hex[:8]}"
    job_dir = LOCAL_JOBS_DIR / new_job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_video_path = job_dir / "input_video.mp4"

    if video_file and video_file.filename:
        with open(input_video_path, "wb") as f:
            f.write(await video_file.read())
    elif existing_video_path and Path(existing_video_path).exists():
        shutil.copy2(Path(existing_video_path), input_video_path)
    else:
        raise HTTPException(status_code=400, detail="Please upload or specify an input video.")

    job_registry[new_job_id] = {
        "job_id": new_job_id,
        "state": "pending",
        "logs": "",
        "video_path": str(input_video_path),
        "output_path": str(OUTPUTS_DIR / f"{new_job_id}_final_lipsynced_video.mp4"),
    }

    thread = threading.Thread(
        target=_run_unified_studio_pipeline,
        args=(new_job_id, input_video_path, job_dir),
        daemon=True,
    )
    thread.start()

    return {"job_id": new_job_id, "status": "started"}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_registry[job_id]


@app.get("/api/video/{job_id}/output")
def get_output_video(job_id: str):
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    out_path = Path(job_registry[job_id]["output_path"])
    if not out_path.exists():
        raise HTTPException(status_code=404, detail="Output video not ready")
    return FileResponse(str(out_path), media_type="video/mp4")


@app.get("/api/video/{job_id}/original")
def get_original_video(job_id: str):
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail="Job not found")
    v_path = Path(job_registry[job_id]["video_path"])
    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Original video not found")
    return FileResponse(str(v_path), media_type="video/mp4")


@app.get("/api/video/{job_id}/dubbed")
def get_dubbed_video(job_id: str):
    job_dir = LOCAL_JOBS_DIR / job_id
    d_path = job_dir / "final_dubbed_video.mp4"
    if not d_path.exists():
        raise HTTPException(status_code=404, detail="Dubbed video not found")
    return FileResponse(str(d_path), media_type="video/mp4")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================")
    print(f"  Nativox Universal Studio (Stage 00 Dubbing + LipSync)")
    print(f"  URL: {url}")
    print(f"=======================================================\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
