"""
Core FFmpeg merge engine for Stage 7: Merge MP3 with MP4.

Replaces the original audio track in a source video with a dubbed MP3,
producing a final MP4 with original video frames preserved (copy-mode remux)
and the new audio transcoded to AAC for maximum container compatibility.
"""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path


# ── Storage paths (gitignored via root .gitignore) ─────────────────────────

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "outputs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# ── FFmpeg / FFprobe discovery ─────────────────────────────────────────────


def find_ffmpeg() -> str:
    """
    Locate the FFmpeg binary.

    Checks system PATH first, then falls back to the WinGet installation
    directory (same pattern used by Stage 1).
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin and os.path.exists(ffmpeg_bin):
        return ffmpeg_bin

    # WinGet fallback (Windows)
    winget_packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget_packages.exists():
        matches = list(winget_packages.glob("**/ffmpeg.exe"))
        if matches:
            return str(matches[0])

    raise FileNotFoundError(
        "FFmpeg binary was not found. "
        "Install FFmpeg using 'winget install Gyan.FFmpeg' (Windows) "
        "or 'brew install ffmpeg' (macOS) and restart the server."
    )


def find_ffprobe() -> str:
    """
    Locate the FFprobe binary (ships alongside FFmpeg).
    """
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin and os.path.exists(ffprobe_bin):
        return ffprobe_bin

    # Derive from FFmpeg location (same directory)
    try:
        ffmpeg_path = Path(find_ffmpeg())
        ffprobe_path = ffmpeg_path.parent / (
            "ffprobe.exe" if os.name == "nt" else "ffprobe"
        )
        if ffprobe_path.exists():
            return str(ffprobe_path)
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        "FFprobe binary was not found. It typically ships alongside FFmpeg."
    )


# ── Media probing ──────────────────────────────────────────────────────────


def probe_media(file_path: Path) -> dict:
    """
    Extract duration, codecs, resolution, and file size using FFprobe.

    Returns a dict with keys: duration, video_codec, audio_codec,
    resolution, file_size_mb.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ffprobe = find_ffprobe()

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr[:500]}")

    data = json.loads(result.stdout)

    # Extract stream info
    video_codec = ""
    audio_codec = ""
    resolution = ""

    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "")
        if codec_type == "video" and not video_codec:
            video_codec = stream.get("codec_name", "unknown")
            width = stream.get("width", 0)
            height = stream.get("height", 0)
            if width and height:
                resolution = f"{width}x{height}"
        elif codec_type == "audio" and not audio_codec:
            audio_codec = stream.get("codec_name", "unknown")

    # Extract duration and size
    fmt = data.get("format", {})
    raw_duration = float(fmt.get("duration", 0))
    file_size_bytes = int(fmt.get("size", 0))

    # Format duration as HH:MM:SS.mmm
    hours = int(raw_duration // 3600)
    minutes = int((raw_duration % 3600) // 60)
    seconds = raw_duration % 60
    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    return {
        "duration": duration_str,
        "duration_seconds": raw_duration,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "resolution": resolution,
        "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
    }


def merge_video_audio(video_path: Path, audio_path: Path) -> tuple[Path, dict]:
    """
    Replace the audio track in a video with a new MP3 audio file.

    Uses FFmpeg copy-mode remux: the video stream is copied byte-for-byte
    (zero quality loss, near-instant) and the MP3 audio is transcoded to
    AAC for maximum MP4 container compatibility.

    Returns a tuple of (output_path, metadata_dict).
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Source video not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Dubbed audio not found: {audio_path}")

    ffmpeg = find_ffmpeg()

    # Probe inputs for metadata
    video_info = probe_media(video_path)
    audio_info = probe_media(audio_path)

    # Validate that source has a video stream
    if not video_info["video_codec"]:
        raise ValueError("The uploaded file does not contain a video stream.")

    # Generate output path
    job_id = uuid.uuid4().hex[:10]
    output_path = STORAGE_DIR / f"dubbed_{job_id}.mp4"

    # FFmpeg command: copy video, transcode audio to AAC, map only first
    # video and first audio stream, use -shortest to handle duration mismatch
    cmd = [
        ffmpeg, "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not output_path.exists():
        err_msg = result.stderr or "Unknown error"
        raise RuntimeError(f"FFmpeg merge failed: {err_msg[-600:]}")

    if output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg produced an empty output file.")

    # Probe the merged output
    output_info = probe_media(output_path)

    metadata = {
        "original_video_duration": video_info["duration"],
        "dubbed_audio_duration": audio_info["duration"],
        "output_duration": output_info["duration"],
        "video_codec": "copy (original preserved)",
        "audio_codec": output_info["audio_codec"],
        "resolution": output_info["resolution"],
        "file_size_mb": output_info["file_size_mb"],
    }

    return output_path, metadata
