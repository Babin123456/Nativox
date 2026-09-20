"""
Pydantic request / response schemas for Stage 7: Merge MP3 with MP4.
"""

from pydantic import BaseModel, Field


# ── Response Models ─────────────────────────────────────────────────────────


class MergeResponse(BaseModel):
    """Response for POST /api/merge."""

    video_url: str = Field(
        ..., description="Relative URL to download the merged dubbed MP4."
    )
    original_video_duration: str = Field(
        ..., description="Duration of the original source video (HH:MM:SS.ms)."
    )
    dubbed_audio_duration: str = Field(
        ..., description="Duration of the dubbed MP3 audio (HH:MM:SS.ms)."
    )
    output_duration: str = Field(
        ..., description="Duration of the final merged output (HH:MM:SS.ms)."
    )
    video_codec: str = Field(
        default="copy", description="Video codec used (copy = no re-encoding)."
    )
    audio_codec: str = Field(
        default="aac", description="Audio codec in the output container."
    )
    resolution: str = Field(
        default="", description="Video resolution (e.g. 1920x1080)."
    )
    file_size_mb: float = Field(
        ..., description="Output file size in megabytes."
    )


class ProbeResponse(BaseModel):
    """Response for GET /api/probe/{filename}."""

    filename: str
    duration: str = Field(default="00:00:00.000", description="Media duration.")
    video_codec: str = Field(default="", description="Video codec if present.")
    audio_codec: str = Field(default="", description="Audio codec if present.")
    resolution: str = Field(default="", description="Video resolution if present.")
    file_size_mb: float = Field(default=0.0, description="File size in megabytes.")
