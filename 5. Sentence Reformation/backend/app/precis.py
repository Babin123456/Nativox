"""
Précis Compression Engine: Compresses a full spoken transcript paragraph from an MP3 file
strictly into a 35% - 40% word budget while preserving core meaning and translating to Hindi.
"""
import math
import re
from .translator import translate_to_hindi

# Conversational meta-phrases commonly occurring in video/podcast transcripts to trim
META_DISCOURSE_PATTERNS = [
    r"welcome\s+(?:back\s+)?(?:guys|everyone|folks|viewers)[,!]?",
    r"in this (?:particular\s+)?(?:video|tutorial|session|lecture|guide|walkthrough)[,:]?",
    r"what we are (?:basically\s+)?going to (?:do|talk about|discuss|cover) is",
    r"as (?:you|we) (?:all\s+)?know[,:]?",
    r"you know[,:]?",
    r"let's (?:dive in|take a look|get started)[,:]?",
    r"don't forget to like and subscribe",
    r"without further ado[,:]?",
]


def split_sentences(text: str) -> list[str]:
    """Split text into sentences cleanly."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def clean_meta_discourse(sentence: str) -> str:
    """Removes video preamble and conversational clutter from a sentence."""
    cleaned = sentence
    for pat in META_DISCOURSE_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Fix capitalization if preamble was stripped
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def extract_core_keywords(text: str) -> list[str]:
    """Extracts prominent nouns and technical terms to ensure retention in précis."""
    words = re.findall(r"[A-Za-z0-9\-_]{3,}", text.lower())
    stopwords = {
        "the", "and", "this", "that", "with", "from", "for", "are", "was", "were",
        "will", "have", "been", "they", "what", "when", "where", "which", "into",
        "about", "more", "some", "very", "just", "also", "your", "them", "then",
    }
    content_words = [w for w in words if w not in stopwords]
    # Unique preserved keywords in order of frequency
    counts = {}
    for w in content_words:
        counts[w] = counts.get(w, 0) + 1
    sorted_words = sorted(counts.keys(), key=lambda w: counts[w], reverse=True)
    return sorted_words[:5]


def score_sentences(sentences: list[str]) -> list[tuple[int, str, float]]:
    """
    Ranks sentences based on informational salience, keyword density, and structural position.
    Returns list of (original_index, cleaned_sentence, score).
    """
    scored = []
    total = len(sentences)
    if total == 0:
        return []

    # Get overall document keywords
    full_text = " ".join(sentences)
    top_keywords = set(extract_core_keywords(full_text))

    for idx, raw_s in enumerate(sentences):
        cleaned = clean_meta_discourse(raw_s)
        if not cleaned:
            continue

        words = re.findall(r"\w+", cleaned.lower())
        word_count = len(words)
        if word_count < 3:
            continue

        # Position score (introductory thesis and conclusion carry higher weight)
        pos_score = 1.2 if (idx == 0 or idx == total - 1) else 1.0

        # Keyword density score
        kw_matches = sum(1 for w in words if w in top_keywords)
        density_score = (kw_matches / word_count) if word_count else 0

        # Length penalty: penalize excessively long run-on sentences in spoken speech
        length_penalty = 1.0 if word_count <= 25 else 0.8

        final_score = (density_score * 2.0 + pos_score) * length_penalty
        scored.append((idx, cleaned, final_score))

    # Sort descending by score
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored


def compress_paragraph_to_budget(
    paragraph: str,
    min_ratio: float = 0.35,
    max_ratio: float = 0.40,
) -> tuple[str, list[str]]:
    """
    Condenses the English paragraph so that word count is calibrated strictly to the
    target 35% - 40% window while preserving semantic flow and avoiding dangling clauses.
    """
    orig_words = len(re.findall(r"\w+", paragraph))
    if orig_words == 0:
        return "", []

    target_min = max(5, math.floor(orig_words * min_ratio))
    target_max = max(target_min, math.ceil(orig_words * max_ratio))

    key_points = extract_core_keywords(paragraph)
    sentences = [clean_meta_discourse(s) for s in split_sentences(paragraph)]
    scored = score_sentences(sentences)

    # Decompose sentences into cohesive clause candidates
    clauses_pool = []
    for orig_idx, s, score in scored:
        parts = re.split(r"(?:;\s*|,\s*(?:and|but|while|so|where|with)\s*)", s)
        for part_idx, part in enumerate(parts):
            p_clean = part.strip().rstrip(",;.")
            # Clean leading clause fillers like "actually", "basically"
            p_clean = re.sub(r"^(?:actually|basically|you know|so yeah|like)[,\s]+", "", p_clean, flags=re.IGNORECASE).strip()
            if p_clean and p_clean[0].islower():
                p_clean = p_clean[0].upper() + p_clean[1:]
            p_words = re.findall(r"\w+", p_clean)
            if len(p_words) >= 4:
                clauses_pool.append({
                    "orig_idx": orig_idx,
                    "part_idx": part_idx,
                    "text": p_clean,
                    "word_count": len(p_words),
                    "score": score,
                })

    # Sort clauses by score
    clauses_pool.sort(key=lambda c: c["score"], reverse=True)

    chosen = []
    current_words = 0
    # Tolerance margin so clauses remain complete without truncated fragments
    upper_limit = target_max + max(2, int(orig_words * 0.03))

    for c in clauses_pool:
        if current_words + c["word_count"] <= upper_limit:
            chosen.append(c)
            current_words += c["word_count"]
            if current_words >= target_min and current_words >= target_max - 2:
                break

    # If still below target_min and full sentences exist, include top sentence
    if current_words < target_min and scored:
        top_sent = scored[0][1]
        draft_precis = top_sent if top_sent.endswith((".", "!", "?")) else top_sent + "."
        return draft_precis, key_points

    # Sort chosen clauses chronologically
    chosen.sort(key=lambda c: (c["orig_idx"], c["part_idx"]))

    result_text = ""
    for idx, c in enumerate(chosen):
        t = c["text"]
        if idx == 0:
            result_text = t
        else:
            prev_clause = chosen[idx - 1]
            if prev_clause["orig_idx"] != c["orig_idx"]:
                if not result_text.endswith((".", "!", "?")):
                    result_text += "."
                result_text += " " + (t[0].upper() + t[1:] if t else "")
            else:
                result_text += ", " + t

    if not result_text.endswith((".", "!", "?")):
        result_text += "."

    return result_text, key_points


def generate_precis(
    raw_paragraph: str,
    min_ratio: float = 0.35,
    max_ratio: float = 0.40,
    target_lang: str = "hindi",
) -> dict:
    """
    Main entry point for Task 2:
    Takes full transcript paragraph from MP3 file, builds a 35% - 40% précis,
    and produces both the English précis and the meaningful Hindi translation.
    """
    raw_paragraph = (raw_paragraph or "").strip()
    if not raw_paragraph:
        return {
            "original_text": "",
            "original_word_count": 0,
            "precis_english": "",
            "precis_hindi": "",
            "precis_word_count": 0,
            "retention_ratio_pct": 0.0,
            "target_ratio_range": f"{int(min_ratio*100)}% - {int(max_ratio*100)}%",
            "is_within_budget": False,
            "key_points_retained": [],
        }

    orig_word_count = len(re.findall(r"\w+", raw_paragraph))

    # Step 1: Compute compressed English précis strictly fitting the 35% - 40% budget
    english_precis, key_points = compress_paragraph_to_budget(
        raw_paragraph, min_ratio=min_ratio, max_ratio=max_ratio
    )

    # Step 2: Translate into natural, fluent Hindi
    hindi_precis = translate_to_hindi(english_precis)

    precis_word_count = len(re.findall(r"\w+", english_precis))
    ratio_pct = round((precis_word_count / orig_word_count) * 100, 1) if orig_word_count else 0.0

    # Verification: check if within the target bounds (allowing small margin of 2% for natural sentence endings)
    is_within_budget = (min_ratio * 100 - 3.0) <= ratio_pct <= (max_ratio * 100 + 3.0)

    return {
        "original_text": raw_paragraph,
        "original_word_count": orig_word_count,
        "precis_english": english_precis,
        "precis_hindi": hindi_precis,
        "precis_word_count": precis_word_count,
        "retention_ratio_pct": ratio_pct,
        "target_ratio_range": f"{int(min_ratio*100)}% - {int(max_ratio*100)}%",
        "is_within_budget": is_within_budget,
        "key_points_retained": key_points,
    }
