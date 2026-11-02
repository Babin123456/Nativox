"""
Script-aware multilingual keyword extraction (single-word output).

Approach
--------
This is a RAKE (Rapid Automatic Keyword Extraction) variant adapted to
work across English, Hindi, Bengali and free code-mixing of the three,
without running separate per-language NLP pipelines and merging results.

Standard RAKE scores multi-word phrases. This project only needs
single-word keywords, so the algorithm keeps RAKE's *scoring* idea but
changes what gets returned:

  1. Split text into sentences on punctuation.
  2. Within each sentence, cut at stopwords - a maximal run of
     consecutive content (non-stopword) words is a "candidate phrase".
     This step is still needed even for single-word output, because it
     is what guarantees a stopword can never end up in the result: a
     word only ever enters a candidate phrase if it is NOT in the
     combined English + Hindi + Bengali stopword set.
  3. Score each unique word by degree(word) / frequency(word), where
     degree counts how often a word co-occurs with other words inside
     candidate phrases (a proxy for how "central"/important it is,
     rather than plain frequency).
  4. Rank individual words by that score and return the top N - never
     multi-word phrases.

The multilingual part is in step 2: because the stopword set is the
*union* of English, Hindi and Bengali stopwords, a single pass finds
content words correctly regardless of which script(s) a sentence
mixes - no language identification of the whole sentence is needed up
front, only per-word script tagging (used afterwards, purely for the
EN/HI/BN/Mixed label shown in the UI).
"""

import re
from collections import defaultdict

from .stopwords import ALL_STOPWORDS
from .language_utils import detect_word_lang

# Sentence/phrase-breaking punctuation, including the Devanagari/Bengali
# "purna virama" danda (।) and double danda (॥) used as full stops.
_SENTENCE_DELIMS = re.compile(
    r"[.!?,;:\n\r\t।॥\-\u2013\u2014\"'()\[\]{}<>/\\|~`^*_=+@#$%&]+"
)

# Unicode-aware "word" = a run of alphabetic characters drawn from
# Latin, Devanagari, or Bengali. Note: Python's built-in re module does
# NOT treat combining marks (vowel signs / matras, virama) as "\w", so
# a plain \w-based pattern silently shreds Devanagari/Bengali words into
# their consonant skeletons. We match the full Unicode blocks instead,
# which keeps matras and virama attached to their base consonant.
_WORD_RE = re.compile(
    r"[A-Za-zÀ-ÖØ-öø-ÿ\u0900-\u097F\u0980-\u09FF]+",
    re.UNICODE,
)

_MIN_WORD_LEN = 1
_MAX_PHRASE_WORDS = 5  # guard against pathological one-giant-phrase input


def _split_into_candidate_phrases(text: str):
    """Return a list of phrases, each a list of original-case word strings."""
    phrases = []
    for sentence in _SENTENCE_DELIMS.split(text):
        words = _WORD_RE.findall(sentence)
        current = []
        for w in words:
            if len(w) < _MIN_WORD_LEN:
                continue
            if w.lower() in ALL_STOPWORDS:
                if current:
                    phrases.append(current)
                    current = []
            else:
                current.append(w)
                if len(current) >= _MAX_PHRASE_WORDS:
                    phrases.append(current)
                    current = []
        if current:
            phrases.append(current)
    return phrases


import math


def _calculate_adaptive_cutoff(ranked: list[dict], min_k: int = 2, max_k: int = 18) -> int:
    """
    Intelligently determine required salient keyword count using
    score gradient analysis (knee / elbow detection) and relative salience.
    """
    n = len(ranked)
    if n <= 3:
        return n

    # Dynamic target bounds based on candidate size (sublinear square-root scaling)
    dynamic_min = max(min_k, min(3, n))
    dynamic_max = min(n, max(dynamic_min, min(max_k, round(2.0 * math.sqrt(n)))))

    max_score = ranked[0]["score"] if ranked and ranked[0]["score"] > 0 else 1.0
    scores = [r["score"] for r in ranked]

    # 1. Look for steep relative salience drop (candidates falling below ~40% of peak score)
    cutoff = dynamic_max
    for i in range(dynamic_min, min(n, dynamic_max + 1)):
        rel = scores[i - 1] / max_score
        if rel < 0.42:
            cutoff = i - 1
            break

    # 2. Knee / Elbow detection: locate steepest score drop within [dynamic_min, dynamic_max]
    best_drop_idx = None
    max_drop = 0.0
    for i in range(dynamic_min - 1, min(n - 1, dynamic_max)):
        drop = scores[i] - scores[i + 1]
        if drop > max_drop:
            max_drop = drop
            best_drop_idx = i + 1

    if best_drop_idx is not None and max_drop >= 0.5:
        cutoff = min(cutoff, best_drop_idx)

    # Clamp strictly within [dynamic_min, dynamic_max]
    final_k = max(dynamic_min, min(cutoff, dynamic_max, n))
    return final_k


def extract_keywords(text: str, top_n: int | None = None):
    """
    Extract salient keywords from multilingual text.
    If top_n is None or <= 0, automatically detects the required keyword
    count using adaptive knee drop-off and relative salience scoring.
    """
    text = (text or "").strip()
    if not text:
        return []

    phrases = _split_into_candidate_phrases(text)
    if not phrases:
        return []

    freq = defaultdict(int)
    degree = defaultdict(int)
    surface_form = {}  # lowercase word -> first-seen original casing
    for phrase in phrases:
        length = len(phrase)
        for w in phrase:
            wl = w.lower()
            freq[wl] += 1
            degree[wl] += length  # co-occurrence with every word in the phrase, incl. itself
            surface_form.setdefault(wl, w)

    word_score = {w: degree[w] / freq[w] for w in freq}

    results = []
    for wl, score in word_score.items():
        surface = surface_form[wl]
        results.append({
            "word": surface,
            "score": score,
            "language": detect_word_lang(surface),
        })

    # Rank by score, breaking ties by raw frequency (more mentions wins).
    ranked = sorted(results, key=lambda r: (r["score"], freq[r["word"].lower()]), reverse=True)

    if top_n is not None and top_n > 0:
        top = ranked[:top_n]
    else:
        cutoff = _calculate_adaptive_cutoff(ranked)
        top = ranked[:cutoff]

    max_score = top[0]["score"] if top else 1.0
    for r in top:
        r["score"] = round(r["score"], 2)
        r["relative_score"] = round(100 * r["score"] / max_score, 1) if max_score else 0.0

    return top


def extract_keywords_in_sequence(text: str, allowed_words: set[str] | list[str] | None = None):
    """
    Return extracted keywords in chronological appearance order.
    If allowed_words is provided (e.g. from intelligent salient extraction),
    only words that passed the salience filter are returned, deduplicated.
    If allowed_words is None, returns all non-stopwords in appearance order.
    """
    phrases = _split_into_candidate_phrases(text)
    ordered = []
    seen = set()
    allowed_set = {w.lower() for w in allowed_words} if allowed_words is not None else None
    for phrase in phrases:
        for w in phrase:
            wl = w.lower()
            if allowed_set is not None:
                if wl in allowed_set and wl not in seen:
                    seen.add(wl)
                    ordered.append(w)
            else:
                ordered.append(w)
    return ordered

