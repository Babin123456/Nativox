"""
Text to Keyword - backend entrypoint.

Run with:
    uvicorn main:app --reload --port 8003

Then open http://127.0.0.1:8003 in a browser - this same process serves
both the API (under /api) and the static frontend (everything else).
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.keyword_extractor import extract_keywords, extract_keywords_in_sequence
from app.language_utils import LANG_LABELS

app = FastAPI(
    title="Text to Keyword",
    description=(
        "Extracts single-word keywords (no stopwords, no multi-word "
        "phrases) from English, Hindi, Bengali, and freely code-mixed "
        "text using a script-aware RAKE scoring algorithm."
    ),
    version="1.0.0",
)

# Permissive CORS so the frontend can be served separately during
# development (e.g. opened as a plain file, or from a different port).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    text: str = Field(..., description="Input text - English, Hindi, Bengali, or a mix")
    top_n: int | None = Field(None, ge=1, le=50, description="Maximum number of keywords to return, or None for auto-salience extraction")
    mode: str | None = Field("auto", description="Extraction mode: 'auto' for intelligent content-aware extraction, 'manual' for fixed top_n")


class KeywordOut(BaseModel):
    word: str
    score: float
    relative_score: float
    language: str | None


class ExtractResponse(BaseModel):
    keywords: list[KeywordOut]
    keywords_in_order: list[str]
    language_labels: dict
    is_auto: bool = True
    total_extracted: int = 0


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/extract-keywords", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    # Determine effective top_n: None means adaptive content-aware extraction
    effective_top_n = (
        req.top_n
        if (req.mode == "manual" and req.top_n is not None)
        else (req.top_n if req.top_n is not None and req.mode != "auto" else None)
    )
    keywords = extract_keywords(req.text, top_n=effective_top_n)
    salient_set = {k["word"] for k in keywords}
    keywords_in_order = extract_keywords_in_sequence(
        req.text, allowed_words=salient_set if salient_set else None
    )
    return {
        "keywords": keywords,
        "keywords_in_order": keywords_in_order,
        "language_labels": LANG_LABELS,
        "is_auto": effective_top_n is None,
        "total_extracted": len(keywords),
    }



# --- Static assets (favicon) and service endpoints --------------------
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_frontend() -> HTMLResponse:
    """Serve the single-page frontend."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Nativox Text to Keyword Online</h1>")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def serve_favicon():
    favicon_path = FRONTEND_DIR / "favicon.webp"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")
