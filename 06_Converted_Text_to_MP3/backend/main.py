"""
Nativox — Stage 6: Converted Text to MP3 (Hindi Speech Synthesis)
-----------------------------------------------------------------
Takes Hindi text output from Stage 5(b) and synthesizes natural-sounding
speech as a downloadable MP3 using Microsoft Edge Neural Voices.

Run from inside the backend/ folder:
    uvicorn main:app --reload --port 8013
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import SynthesizeRequest, SynthesizeResponse, VoicesResponse
from app.tts_engine import get_available_voices, synthesize_speech

app = FastAPI(
    title="Nativox — Hindi Text to MP3",
    description=(
        "Stage 6 of the Nativox pipeline. Converts Hindi text into "
        "natural-sounding speech MP3 files using Edge Neural TTS."
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

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage" / "outputs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# ── Health ──────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "stage-6-text-to-mp3",
        "engine": "edge-tts",
        "supported_locale": "hi-IN",
    }


# ── Speech Synthesis ────────────────────────────────────────────────────────


@app.post("/api/synthesize", response_model=SynthesizeResponse)
async def synthesize_endpoint(request: SynthesizeRequest):
    """
    Synthesize Hindi text into an MP3 audio file.

    Accepts text, voice selection, rate, and pitch parameters.
    Returns a URL to download the generated audio.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    try:
        from app.tts_engine import _synthesize_async
        output_path = await _synthesize_async(
            text=text,
            voice=request.voice,
            rate=request.rate,
            pitch=request.pitch,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Speech synthesis failed: {exc}"
        ) from exc

    return {
        "audio_url": f"/api/audio/{output_path.name}",
        "voice_used": request.voice,
        "text_length": len(text),
        "word_count": len(text.split()),
    }


# ── Audio File Serving ──────────────────────────────────────────────────────


@app.get("/api/audio/{filename}")
def serve_audio(filename: str):
    """Serve a previously synthesized MP3 file."""
    # Sanitize filename to prevent directory traversal
    safe_name = Path(filename).name
    audio_path = STORAGE_DIR / safe_name

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")

    return FileResponse(
        str(audio_path),
        media_type="audio/mpeg",
        filename=safe_name,
    )


# ── Voice Listing ──────────────────────────────────────────────────────────


@app.get("/api/voices", response_model=VoicesResponse)
async def list_voices(locale: str = "hi-IN"):
    """Return all available Edge-TTS voices for the given locale."""
    try:
        voices = await get_available_voices(locale)
    except Exception:
        # Fallback: return the two known Hindi voices if network fetch fails
        voices = [
            {
                "short_name": "hi-IN-SwaraNeural",
                "friendly_name": "Swara (Female, Hindi)",
                "gender": "Female",
                "locale": "hi-IN",
            },
            {
                "short_name": "hi-IN-MadhurNeural",
                "friendly_name": "Madhur (Male, Hindi)",
                "gender": "Male",
                "locale": "hi-IN",
            },
        ]

    return {
        "locale_filter": locale,
        "count": len(voices),
        "voices": voices,
    }


# ── Frontend Static Serving ────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Nativox Stage 6 Backend is Running. Frontend not found."}


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def favicon():
    fav = FRONTEND_DIR / "favicon.webp"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")
