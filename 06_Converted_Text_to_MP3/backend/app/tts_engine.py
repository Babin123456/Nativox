"""
Core TTS synthesis engine powered by Microsoft Edge Neural Voices (edge-tts).

Provides high-quality Hindi speech synthesis without API keys or GPU.
"""

import asyncio
import uuid
from pathlib import Path

# pyrefly: ignore [missing-import]
import edge_tts

# ── Storage paths (gitignored via root .gitignore) ─────────────────────────

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage" / "outputs"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# ── Default voices ─────────────────────────────────────────────────────────

DEFAULT_VOICE = "hi-IN-SwaraNeural"  # Female Hindi voice
FALLBACK_VOICE = "hi-IN-MadhurNeural"  # Male Hindi voice


async def _synthesize_async(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    """
    Run edge-tts synthesis and write the result to an MP3 file.

    Returns the Path to the generated MP3.
    """
    job_id = uuid.uuid4().hex[:12]
    output_path = STORAGE_DIR / f"tts_{job_id}.mp3"

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(str(output_path))

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("TTS synthesis produced an empty or missing file.")

    return output_path


def synthesize_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> Path:
    """
    Synchronous wrapper around the async edge-tts synthesizer.

    Safe to call from FastAPI sync endpoints (creates its own event loop
    if one is not already running, otherwise schedules on the running loop).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an already-running async context (e.g. uvicorn).
        # Create a new thread-based loop to avoid nested-loop errors.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                _synthesize_async(text, voice, rate, pitch),
            )
            return future.result(timeout=120)
    else:
        return asyncio.run(_synthesize_async(text, voice, rate, pitch))


async def get_available_voices(locale: str = "hi-IN") -> list[dict]:
    """
    Fetch all available Edge-TTS voices and filter by locale prefix.

    Returns a list of dicts with keys: short_name, friendly_name, gender, locale.
    """
    all_voices = await edge_tts.list_voices()
    filtered = []
    for v in all_voices:
        if v.get("Locale", "").startswith(locale):
            filtered.append(
                {
                    "short_name": v["ShortName"],
                    "friendly_name": v.get("FriendlyName", v["ShortName"]),
                    "gender": v.get("Gender", "Unknown"),
                    "locale": v.get("Locale", locale),
                }
            )
    # Sort female voices first, then alphabetically
    filtered.sort(key=lambda x: (x["gender"] != "Female", x["short_name"]))
    return filtered
