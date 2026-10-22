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
from fastapi.responses import FileResponse
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
    top_n: int = Field(15, ge=1, le=50, description="Maximum number of keywords to return")


class KeywordOut(BaseModel):
    word: str
    score: float
    relative_score: float
    language: str | None


class ExtractResponse(BaseModel):
    keywords: list[KeywordOut]
    keywords_in_order: list[str]
    language_labels: dict


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/extract-keywords", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    keywords = extract_keywords(req.text, top_n=req.top_n)
    keywords_in_order = extract_keywords_in_sequence(req.text)
    return {
        "keywords": keywords,
        "keywords_in_order": keywords_in_order,
        "language_labels": LANG_LABELS,
    }


# --- Static assets (favicon) and service endpoints --------------------
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    """Service status and API documentation entry point."""
    return {
        "service": "Text to Keyword Extractor",
        "stage": "03_Text_to_Keyword",
        "status": "online",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def serve_favicon():
    favicon_path = STATIC_DIR / "favicon.webp"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")
