import os
import shutil
import sys
import uuid
from pathlib import Path

# Add parent directory (LipSync_Babin root) to sys.path so config, pipeline, etc. resolve
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from config import PipelineConfig
from pipeline import run_pipeline
from translation.translator import build_translator

app = FastAPI(title="Nativox Web UI")

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUTS_DIR = Path("outputs").resolve()
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Mount outputs for video playback
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = TEMPLATES_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

@app.post("/api/dub")
async def dub_video(
    file: UploadFile = File(...),
    lang: str = Form("hi"),
    tts: str = Form("free"),
    enhance: bool = Form(True)
):
    req_id = str(uuid.uuid4())[:8]
    work_dir = Path("work") / req_id
    work_dir.mkdir(parents=True, exist_ok=True)

    input_path = work_dir / file.filename
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_filename = f"dubbed_{req_id}_{lang}.mp4"
    output_path = OUTPUTS_DIR / output_filename

    try:
        cfg = PipelineConfig(
            input_video=input_path,
            target_lang=lang,
            output_video=output_path,
            work_dir=work_dir,
            dry_run=False
        )
        run_pipeline(cfg, enhance_face=enhance, tts_backend=tts, preserve_bgm=True)

        # Retrieve transcript and translation preview
        source_audio = work_dir / f"{input_path.stem}_source.wav"
        if not source_audio.exists():
            source_audio = work_dir / "source.wav"
        translator = build_translator()
        transcript = translator.transcribe(source_audio) if source_audio.exists() else "Completed"
        translated = translator.translate(transcript, target_lang=lang, speaker_gender="Male")

        return {
            "status": "success",
            "output_url": f"/outputs/{output_filename}",
            "transcript": transcript,
            "translated": translated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=7860, reload=False)
