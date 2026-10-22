"""
Nativox — Keyword Translation stage
FastAPI backend + single-page frontend served from the same process.

Run from inside the backend/ folder:
    uvicorn main:app --reload --port 8011
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import LANG_CODES, LANG_LABELS
from app.schemas import (
    TranslateRequest,
    TranslateResponse,
    BatchTranslateRequest,
    BatchTranslateResponse,
)
from app.translate_service import translate_keyword, translate_keywords_batch

app = FastAPI(title="Nativox — Keyword Translation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "keyword-translation"}


@app.post("/api/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        result = translate_keyword(text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}")
    return result


@app.post("/api/translate-batch", response_model=BatchTranslateResponse)
def translate_batch(request: BatchTranslateRequest):
    target = request.target_language.strip().lower()
    if target not in LANG_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"target_language must be one of: {', '.join(LANG_CODES.keys())}",
        )

    cleaned_keywords = [k for k in request.keywords if k and k.strip()]
    if not cleaned_keywords:
        raise HTTPException(status_code=400, detail="No non-empty keywords provided.")

    try:
        results = translate_keywords_batch(cleaned_keywords, target)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}")

    return {
        "target_language": target,
        "target_label": LANG_LABELS[target],
        "results": results,
    }


# Serve static assets (favicon)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def root():
    """Redirect to interactive Swagger UI documentation."""
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def favicon():
    favicon_path = STATIC_DIR / "favicon.webp"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")
