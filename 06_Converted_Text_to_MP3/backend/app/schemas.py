"""
Pydantic request / response schemas for Stage 6: Text-to-Speech synthesis.
"""

from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    """Body for POST /api/synthesize."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Hindi (or English) text to synthesize into speech.",
    )
    voice: str = Field(
        default="hi-IN-SwaraNeural",
        description="Edge-TTS voice short name (e.g. hi-IN-SwaraNeural, hi-IN-MadhurNeural).",
    )
    rate: str = Field(
        default="+0%",
        description="Speech rate adjustment (e.g. '+10%', '-20%', '+0%').",
    )
    pitch: str = Field(
        default="+0Hz",
        description="Pitch adjustment (e.g. '+5Hz', '-10Hz', '+0Hz').",
    )


class SynthesizeResponse(BaseModel):
    """Response for POST /api/synthesize."""

    audio_url: str = Field(
        ..., description="Relative URL to download the synthesized MP3."
    )
    voice_used: str = Field(..., description="The voice short name that was used.")
    text_length: int = Field(..., description="Character count of the input text.")
    word_count: int = Field(..., description="Word count of the input text.")


# ── Voice Listing Models ───────────────────────────────────────────────────

class VoiceInfo(BaseModel):
    """Single voice entry returned by GET /api/voices."""

    short_name: str
    friendly_name: str
    gender: str
    locale: str


class VoicesResponse(BaseModel):
    """Response for GET /api/voices."""

    locale_filter: str
    count: int
    voices: list[VoiceInfo]
