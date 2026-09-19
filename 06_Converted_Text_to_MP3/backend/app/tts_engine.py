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

# ── Language detection and allowed locales ─────────────────────────────────

SUPPORTED_LANGUAGES = {
    "hi": {
        "name": "Hindi",
        "default_voice": "hi-IN-SwaraNeural",
        "fallback_voice": "hi-IN-MadhurNeural",
        "locales": ["hi-IN"],
    },
    "bn": {
        "name": "Bengali",
        "default_voice": "bn-IN-BashkarNeural",
        "fallback_voice": "bn-IN-TanishaaNeural",
        "locales": ["bn-IN", "bn-BD"],
    },
}

DEFAULT_VOICE = "hi-IN-SwaraNeural"
FALLBACK_VOICE = "hi-IN-MadhurNeural"


def detect_language(text: str) -> tuple[str, str]:
    """
    Detect whether the given text is in a supported target dubbed language (Bengali or Hindi).

    Returns a tuple of (lang_code, language_name), e.g. ('bn', 'Bengali').
    Raises ValueError if English or unsupported language characters are detected.
    """
    import re

    cleaned = re.sub(r"[\s\d\W_]+", "", text)
    if not cleaned:
        raise ValueError("Input contains no valid linguistic text characters.")

    bengali_chars = len(re.findall(r"[\u0980-\u09FF]", cleaned))
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", cleaned))
    latin_chars = len(re.findall(r"[a-zA-Z]", cleaned))

    # Reject English source text — Stage 6 is for target dubbed languages (Bengali or Hindi)
    if latin_chars > 0 and latin_chars >= (bengali_chars + devanagari_chars):
        raise ValueError(
            "English text detected. Stage 6 is the final dubbing stage for target vernacular audio. "
            "Please translate or reform text into Bengali or Hindi (using Stage 5) before speech synthesis."
        )

    valid_count = bengali_chars + devanagari_chars
    if valid_count / len(cleaned) < 0.6:
        raise ValueError(
            "Unsupported language or characters detected. "
            "Stage 6 only synthesizes target dubbed languages: Bengali (বাংলা) and Hindi (हिन्दी)."
        )

    scores = {
        "bn": bengali_chars,
        "hi": devanagari_chars,
    }
    dominant_lang = max(scores, key=scores.get)
    if scores[dominant_lang] == 0:
        raise ValueError(
            "Unsupported text. Only Bengali and Hindi texts can be synthesized into dubbed MP3."
        )

    return dominant_lang, SUPPORTED_LANGUAGES[dominant_lang]["name"]


async def _synthesize_async(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> tuple[Path, str, str]:
    """
    Validate language (Bengali, English, Hindi) and run edge-tts synthesis.

    Returns a tuple of (output_path, detected_lang_code, detected_lang_name).
    """
    lang_code, lang_name = detect_language(text)

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

    return output_path, lang_code, lang_name


def synthesize_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> tuple[Path, str, str]:
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
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                asyncio.run,
                _synthesize_async(text, voice, rate, pitch),
            )
            return future.result(timeout=120)
    else:
        return asyncio.run(_synthesize_async(text, voice, rate, pitch))


async def get_available_voices(locale: str = "all") -> list[dict]:
    """
    Fetch available Edge-TTS voices filtered to target dubbed languages (Bengali and Hindi).

    If locale is 'all' or empty, returns voices for both supported target languages.
    Otherwise filters by prefix (e.g. 'bn', 'hi').
    """
    all_voices = await edge_tts.list_voices()
    filtered = []
    allowed_prefixes = ("bn-", "hi-")

    for v in all_voices:
        v_locale = v.get("Locale", "")
        if not any(v_locale.startswith(p) for p in allowed_prefixes):
            continue

        if locale and locale != "all":
            # Match language prefix like 'bn', 'hi', or exact locale like 'hi-IN'
            if not v_locale.startswith(locale):
                continue

        filtered.append(
            {
                "short_name": v["ShortName"],
                "friendly_name": v.get("FriendlyName", v["ShortName"]),
                "gender": v.get("Gender", "Unknown"),
                "locale": v_locale,
            }
        )

    # Sort female first, then locale, then short_name
    filtered.sort(key=lambda x: (x["gender"] != "Female", x["locale"], x["short_name"]))
    return filtered
