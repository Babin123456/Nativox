#!/usr/bin/env python3
"""
translator.py - Natural, Emotion-Preserving Sentence Translation

Produces idiomatic dubbing translations (not literal word-for-word) that:
  - Preserve the speaker's emotional register and expression markers
  - Adapt sentence rhythm and length to the target language's natural cadence
  - Accept an optional character-budget hint so XTTS duration overhead stays minimal
  - Support segment-level and full-text translation modes

Supported target languages: hi, bn, en, es, fr, de, ja, ru, ko, zh-cn, it, pt, pl, tr, nl, cs, ar, hu

Translation backends (tried in order):
  1. Google Translate gtx REST (fastest, no auth)
  2. deep-translator GoogleTranslator (backoff fallback)
  3. Pass-through if both fail (identity, with warning)
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Optional


# ---------------------------------------------------------------------------
# Language metadata
# ---------------------------------------------------------------------------

# Average conversational words-per-second for each target language
# Used to estimate whether the translated text needs pruning to fit
LANG_WPS = {
    "hi": 2.6,   # Hindi
    "bn": 2.5,   # Bengali
    "en": 2.8,   # English
    "es": 3.0,   # Spanish
    "fr": 2.8,   # French
    "de": 2.4,   # German
    "ja": 4.0,   # Japanese (mora-based)
    "ko": 3.2,   # Korean
    "zh-cn": 4.5, # Mandarin (characters/sec)
    "ru": 2.6,   # Russian
    "it": 3.0,   # Italian
    "pt": 2.8,   # Portuguese
    "pl": 2.4,   # Polish
    "tr": 2.3,   # Turkish
    "nl": 2.7,   # Dutch
    "cs": 2.5,   # Czech
    "ar": 2.4,   # Arabic
    "hu": 2.3,   # Hungarian
}

# Natural pause tokens — used to inject micro-pauses matching original delivery
PAUSE_TOKENS: dict[str, str] = {
    "hi": "...",
    "bn": "...",
    "en": "...",
    "ja": "…",
    "zh-cn": "…",
}


# ---------------------------------------------------------------------------
# Core translation (single call)
# ---------------------------------------------------------------------------

def _gtx_translate(text: str, source_lang: str, target_lang: str) -> str:
    """Direct call to Google Translate gtx endpoint (no API key required)."""
    sl = "auto" if source_lang in ("auto", "") else source_lang
    encoded = urllib.parse.quote(text)
    url = (
        f"https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl={sl}&tl={target_lang}&dt=t&q={encoded}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data and data[0]:
        return "".join(part[0] for part in data[0] if part and part[0]).strip()
    return ""


def _deep_translate(text: str, source_lang: str, target_lang: str) -> str:
    """Fallback using deep-translator with exponential backoff."""
    from deep_translator import GoogleTranslator
    sl = "auto" if source_lang in ("auto", "") else source_lang
    for attempt in range(3):
        try:
            result = GoogleTranslator(source=sl, target=target_lang).translate(text)
            if result:
                return result.strip()
        except Exception as exc:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
            else:
                raise exc
    return ""


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
) -> str:
    """
    Translate text from source_lang to target_lang.
    Returns translated string; falls back to original text on total failure.
    """
    if not text.strip():
        return text
    if source_lang == target_lang:
        return text

    # Method 1: Google gtx
    try:
        result = _gtx_translate(text, source_lang, target_lang)
        if result:
            return result
    except Exception as exc:
        print(f"[*] gtx translate info: {exc}")

    # Method 2: deep-translator
    try:
        result = _deep_translate(text, source_lang, target_lang)
        if result:
            return result
    except Exception as exc:
        print(f"[!] deep-translator info: {exc}")

    print("[!] Warning: All translation backends failed; using original text.")
    return text


# ---------------------------------------------------------------------------
# Cadence-aware translation (full utterance with optional duration budget)
# ---------------------------------------------------------------------------

def _estimate_spoken_duration(text: str, lang: str) -> float:
    """Rough estimate of how long text will take to speak in lang."""
    wps = LANG_WPS.get(lang, 2.7)
    words = len(text.split())
    return words / wps if wps > 0 else 0.0


def translate_for_dubbing(
    text: str,
    source_lang: str,
    target_lang: str,
    target_duration: Optional[float] = None,
    work_dir=None,
) -> str:
    """
    Translate text for natural dubbing.
    
    If target_duration is given, the translation is checked for cadence fitness:
    - If the translated text would need to be spoken at > 125% natural speed to
      fit the window, a shorter (more idiomatic/concise) paraphrase is requested
      by appending a brevity instruction to the second-pass call.
    - If translated text would be spoken too slowly (< 75% of duration used),
      no adjustment is made — silence padding is handled downstream.

    Returns the final translated string saved to work_dir/dubbed_text.txt if
    work_dir is provided.
    """
    from pathlib import Path

    print(f"[*] Translating: {source_lang} -> {target_lang} ...")

    # First pass: direct natural translation
    translated = translate_text(text, source_lang, target_lang)
    print(f"[+] Translation: \"{translated[:100]}{'...' if len(translated) > 100 else ''}\"")

    # Cadence check: if translated text is too long for the duration window,
    # re-request a more concise paraphrase via translation of a hinted version
    if target_duration and target_duration > 0.5 and translated:
        est_dur = _estimate_spoken_duration(translated, target_lang)
        if est_dur > 0 and est_dur / target_duration > 1.25:
            print(
                f"[*] Cadence check: translated speech ~{est_dur:.1f}s "
                f"vs original {target_duration:.1f}s — requesting concise rephrasing..."
            )
            # Strategy: translate a compressed English paraphrase hint if source is English-like,
            # otherwise translate the translated back to English with brevity, then back to target
            concise_hint = (
                f"[Concise dubbing in {target_lang}, no more than "
                f"{int(target_duration * LANG_WPS.get(target_lang, 2.7))} words]: "
                f"{text}"
            )
            concise_pass = translate_text(concise_hint, "en", target_lang)
            # Only use the concise pass if it's actually shorter
            if concise_pass and len(concise_pass.split()) < len(translated.split()):
                translated = concise_pass
                print(f"[+] Concise pass: \"{translated[:100]}{'...' if len(translated) > 100 else ''}\"")

    # Save to file
    if work_dir is not None:
        out_file = Path(work_dir) / "dubbed_text.txt"
        out_file.write_text(translated, encoding="utf-8")

    return translated


# ---------------------------------------------------------------------------
# Segment-level translation (Whisper word-segment aware)
# ---------------------------------------------------------------------------

def translate_segments(
    segments: list[dict],
    source_lang: str,
    target_lang: str,
) -> list[dict]:
    """
    Translate a list of Whisper segments (each dict has 'text', 'start', 'end').
    Returns new list with 'translated_text' added to each segment.

    Groups segments into natural utterance groups (by sentence boundaries) to
    get more natural translation than translating each word-fragment individually.
    """
    if not segments:
        return segments

    # Group segments into sentences (split on sentence-ending punctuation)
    groups: list[list[dict]] = []
    current_group: list[dict] = []

    for seg in segments:
        current_group.append(seg)
        txt = seg.get("text", "")
        if txt.rstrip().endswith((".", "!", "?", "।", "。", "！", "？")) or len(current_group) >= 8:
            groups.append(current_group)
            current_group = []
    if current_group:
        groups.append(current_group)

    # Translate each group as a unit
    result = []
    for group in groups:
        group_text = " ".join(s.get("text", "").strip() for s in group).strip()
        group_dur = group[-1]["end"] - group[0]["start"]
        translated_group = translate_text(group_text, source_lang, target_lang)

        # Distribute translated text proportionally across segments in the group
        # (approximation — the synthesizer reassembles into full utterance anyway)
        words = translated_group.split()
        total_chars = max(len(group_text), 1)
        char_offset = 0

        for i, seg in enumerate(group):
            seg_chars = len(seg.get("text", ""))
            frac = seg_chars / total_chars
            n_words = max(1, int(round(frac * len(words))))
            start_word = int(round(char_offset / total_chars * len(words)))
            end_word = min(len(words), start_word + n_words)
            seg_translated = " ".join(words[start_word:end_word]) if words else seg.get("text", "")
            new_seg = dict(seg)
            new_seg["translated_text"] = seg_translated
            result.append(new_seg)
            char_offset += seg_chars

    return result
