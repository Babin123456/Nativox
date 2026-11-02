"""Nativox lipsync analysis service."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.compare import compare_all
from app.mouth_curve import extract_mouth_curve
from app.plot import plot_curves

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
VIDEO_DIR = BASE_DIR / "videos"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
for directory in (VIDEO_DIR, OUTPUT_DIR, UPLOAD_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nativox Lipsync Analyzer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "lipsync-analyzer"}


@app.post("/api/analyze")
async def analyze(
    real_hindi: UploadFile = File(...),
    dubbed: UploadFile = File(...),
    dubbed_lipsync: UploadFile = File(...),
) -> dict[str, object]:
    """Analyze three videos and save a plot in the output directory."""
    job_id = uuid.uuid4().hex[:10]
    uploads: dict[str, Path] = {}
    files = {
        "real": real_hindi,
        "dubbed": dubbed,
        "dubbed_lipsync": dubbed_lipsync,
    }
    try:
        for name, upload in files.items():
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}:
                raise HTTPException(status_code=400, detail=f"Unsupported video format: {suffix or 'unknown'}")
            path = UPLOAD_DIR / f"{job_id}_{name}{suffix}"
            path.write_bytes(await upload.read())
            uploads[name] = path

        curves: dict[str, object] = {}
        fps: dict[str, float] = {}
        for name, path in uploads.items():
            curve, rate = extract_mouth_curve(path)
            curves[name] = curve
            fps[name] = rate
        scores = compare_all(
            curves["real"],
            curves["dubbed"],
            curves["dubbed_lipsync"],
            fps=fps["real"],
        )
        plot_path = plot_curves(curves, OUTPUT_DIR / f"{job_id}_mouth_curves.png", fps)
        return {
            "job_id": job_id,
            "scores": scores,
            "plot_url": f"/api/output/{plot_path.name}",
            "frames": {name: int(curve.size) for name, curve in curves.items()},
        }
    except HTTPException:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        for path in uploads.values():
            path.unlink(missing_ok=True)


@app.get("/api/output/{filename}")
def output_file(filename: str) -> FileResponse:
    path = OUTPUT_DIR / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Output file not found.")
    return FileResponse(path, media_type="image/png")


if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
