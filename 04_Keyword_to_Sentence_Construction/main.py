"""
main.py
-------
FastAPI application serving the Sentence Construction Engine (Stage 4).
Runs on http://127.0.0.1:8004.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import the inference engine from construct.py
from construct import SentenceConstructor

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
SAVED_MODEL_DIR = BASE_DIR / "saved_model"

app = FastAPI(
    title="Nativox Stage 4 — Keyword to Sentence Construction",
    description="Sequence-to-Sequence neural syntax reconstruction engine converting destructive, jumbled, or broken words into grammatical sentences.",
    version="1.0.0",
)

# CORS middleware for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance (lazy loaded)
_constructor: Optional[SentenceConstructor] = None


def get_constructor() -> SentenceConstructor:
    global _constructor
    if _constructor is None:
        model_path_str = str(SAVED_MODEL_DIR) if SAVED_MODEL_DIR.exists() else "./saved_model"
        _constructor = SentenceConstructor(model_path=model_path_str)
    return _constructor


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class ConstructRequest(BaseModel):
    text: str = Field(..., description="Destructive or jumbled input text")
    num_beams: int = Field(4, ge=1, le=10, description="Number of beams for beam search")
    max_length: int = Field(64, ge=16, le=256, description="Max tokens generated")


class ConstructResponse(BaseModel):
    input_text: str
    output_sentence: str
    latency_ms: float
    num_beams: int
    device: str
    checkpoint_type: str


# ── API Endpoints ───────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    constructor = get_constructor()
    is_finetuned = SAVED_MODEL_DIR.exists() and (SAVED_MODEL_DIR / "config.json").exists()
    return {
        "status": "healthy",
        "stage": "04_Keyword_to_Sentence_Construction",
        "device": str(constructor.device),
        "is_finetuned": is_finetuned,
        "checkpoint": "Fine-Tuned Checkpoint" if is_finetuned else "Zero-Shot T5 Fallback",
    }


@app.post("/api/construct", response_model=ConstructResponse)
def construct_sentence(req: ConstructRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    constructor = get_constructor()
    t0 = time.perf_counter()
    try:
        result = constructor.construct(
            destructive_sentence=text,
            num_beams=req.num_beams,
            max_length=req.max_length,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Construction failed: {exc}") from exc

    latency = (time.perf_counter() - t0) * 1000
    is_finetuned = SAVED_MODEL_DIR.exists() and (SAVED_MODEL_DIR / "config.json").exists()

    return {
        "input_text": text,
        "output_sentence": result,
        "latency_ms": round(latency, 2),
        "num_beams": req.num_beams,
        "device": str(constructor.device),
        "checkpoint_type": "Fine-Tuned Checkpoint" if is_finetuned else "Zero-Shot T5 Fallback",
    }


# ── Frontend Static Files ───────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Nativox Stage 4 Backend is Running. Frontend not found."}


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def favicon():
    fav = FRONTEND_DIR / "favicon.webp"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8004, reload=True)
