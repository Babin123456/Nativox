"""
Nativox — Stage 7: Merge MP3 with MP4 (Final Dubbed Video Assembly)
--------------------------------------------------------------------
Takes the original source MP4 video (from Stage 1) and the target-language
MP3 audio (from Stage 6), replaces the original English audio track with the
dubbed MP3, and produces the final dubbed MP4 with original video frames
preserved via FFmpeg copy-mode remux.

Run from inside the backend/ folder:
    uvicorn main:app --reload --port 8014
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.merger import merge_video_audio, probe_media, find_ffmpeg
from app.schemas import MergeResponse, ProbeResponse

app = FastAPI(
    title="Nativox — Merge MP3 with MP4",
    description=(
        "Stage 7 (Final) of the Nativox pipeline. Merges the original source "
        "video with the target-language dubbed MP3, producing a final MP4 "
        "with the English audio completely replaced."
    ),
    version="1.0.0",
)

# CORS middleware for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}
MAX_FILE_SIZE_MB = 500


# ── Health ──────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    ffmpeg_status = "available"
    try:
        find_ffmpeg()
    except FileNotFoundError:
        ffmpeg_status = "not found"

    return {
        "status": "ok",
        "service": "stage-7-merge-mp3-with-mp4",
        "engine": "ffmpeg (copy-mode remux)",
        "ffmpeg": ffmpeg_status,
    }


# ── Video-Audio Merge ──────────────────────────────────────────────────────


@app.post("/api/merge", response_model=MergeResponse)
async def merge_endpoint(
    video: UploadFile = File(..., description="Original source MP4 video"),
    audio: UploadFile = File(..., description="Dubbed target-language MP3 audio"),
):
    """
    Merge an original video with dubbed audio to produce the final dubbed MP4.

    Removes the original English audio track from the video and attaches the
    dubbed MP3 as the new audio track. Video frames are preserved byte-for-byte
    via copy-mode remux (zero quality loss).
    """
    # Validate video file extension
    video_ext = Path(video.filename or "").suffix.lower()
    if video_ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{video_ext}'. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXT))}",
        )

    # Validate audio file extension
    audio_ext = Path(audio.filename or "").suffix.lower()
    if audio_ext not in ALLOWED_AUDIO_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{audio_ext}'. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXT))}",
        )

    job_id = uuid.uuid4().hex[:10]
    video_path = UPLOAD_DIR / f"{job_id}_video{video_ext}"
    audio_path = UPLOAD_DIR / f"{job_id}_audio{audio_ext}"

    # Stream video upload to disk
    try:
        size = 0
        with open(video_path, "wb") as out_file:
            while chunk := await video.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    out_file.close()
                    video_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video file exceeds {MAX_FILE_SIZE_MB} MB limit.",
                    )
                out_file.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        video_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save video: {exc}") from exc

    # Stream audio upload to disk
    try:
        size = 0
        with open(audio_path, "wb") as out_file:
            while chunk := await audio.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    out_file.close()
                    audio_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Audio file exceeds {MAX_FILE_SIZE_MB} MB limit.",
                    )
                out_file.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        audio_path.unlink(missing_ok=True)
        video_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {exc}") from exc

    # Execute the merge
    try:
        output_path, metadata = merge_video_audio(video_path, audio_path)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=500, detail=str(fnf)) from fnf
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err)) from val_err
    except RuntimeError as rt_err:
        raise HTTPException(status_code=500, detail=str(rt_err)) from rt_err
    finally:
        # Clean up uploaded files regardless of outcome
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)

    return {
        "video_url": f"/api/video/{output_path.name}",
        **metadata,
    }


# ── Video File Serving ─────────────────────────────────────────────────────


@app.get("/api/video/{filename}")
def serve_video(filename: str):
    """Serve a previously merged dubbed MP4 file."""
    safe_name = Path(filename).name
    video_path = OUTPUT_DIR / safe_name

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found.")

    return FileResponse(
        str(video_path),
        media_type="video/mp4",
        filename=safe_name,
    )


# ── Media Probe ────────────────────────────────────────────────────────────


@app.get("/api/probe/{filename}", response_model=ProbeResponse)
def probe_endpoint(filename: str):
    """Return FFprobe metadata for a file in the output directory."""
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        info = probe_media(file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Probe failed: {exc}"
        ) from exc

    return {
        "filename": safe_name,
        "duration": info["duration"],
        "video_codec": info["video_codec"],
        "audio_codec": info["audio_codec"],
        "resolution": info["resolution"],
        "file_size_mb": info["file_size_mb"],
    }


# ── Frontend Static Serving ───────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Nativox Stage 7 Backend is Running. Frontend not found."}


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def favicon():
    fav = FRONTEND_DIR / "favicon.webp"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")
