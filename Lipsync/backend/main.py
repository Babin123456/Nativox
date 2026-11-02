import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.compare import run_comparison
from app.plot import make_plot

BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS = BASE_DIR / "videos"
OUTPUT = BASE_DIR / "output"
FRONTEND = BASE_DIR / "frontend"
VIDEOS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

app = FastAPI(title="Nativox Lip-Sync Evaluation")
app.mount("/output", StaticFiles(directory=OUTPUT), name="output")


def save_upload(upload: UploadFile, name: str) -> Path:
    suffix = Path(upload.filename or "").suffix or ".mp4"
    path = VIDEOS / f"{name}{suffix}"
    with open(path, "wb") as file:
        shutil.copyfileobj(upload.file, file)
    return path


def make_side_by_side(left: Path, right: Path, out_path: Path) -> bool:
    command = [
        "ffmpeg", "-y", "-i", str(left), "-i", str(right),
        "-filter_complex",
        "[0:v]scale=640:360[a];[1:v]scale=640:360[b];[a][b]hstack=inputs=2[v]",
        "-map", "[v]", "-map", "1:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(out_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")


@app.post("/api/compare")
def compare(
    real: UploadFile = File(...),
    dubbed: UploadFile = File(...),
    lipsync: UploadFile | None = File(None),
):
    real_path = save_upload(real, "real_hindi")
    dubbed_path = save_upload(dubbed, "dubbed")

    candidates = {"Dubbed (no lip-sync)": dubbed_path}
    best_path = dubbed_path
    if lipsync is not None:
        lipsync_path = save_upload(lipsync, "dubbed_lipsync")
        candidates["Dubbed + Wav2Lip"] = lipsync_path
        best_path = lipsync_path

    try:
        results, series = run_comparison(real_path, candidates)
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    make_plot(results, series, OUTPUT / "compare_plot.png")
    has_video = make_side_by_side(real_path, best_path, OUTPUT / "side_by_side.mp4")

    return {
        "results": results,
        "plot": "/output/compare_plot.png",
        "video": "/output/side_by_side.mp4" if has_video else None,
    }
