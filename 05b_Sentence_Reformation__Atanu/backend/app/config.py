"""
Configuration and constants for Stage 5: Sentence Reformation & Précis Compression.
"""
from pathlib import Path

# Server settings
DEFAULT_PORT = 8012

# Compression Targets (Sir's directive: 35% - 40%)
DEFAULT_MIN_COMPRESSION = 0.35
DEFAULT_MAX_COMPRESSION = 0.40

# Spoken English fillers & disfluencies to eliminate
ENGLISH_DISFLUENCIES = [
    r"\bum+\b",
    r"\buh+\b",
    r"\ber+\b",
    r"\bah+\b",
    r"\byou know\b",
    r"\bbasically\b",
    r"\blike\b",
    r"\bactually\b",
    r"\bso yeah\b",
    r"\bright now\b",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\bi mean\b",
]

# Spoken Hindi fillers if any code-mixed speech arrives
HINDI_DISFLUENCIES = [
    r"\bमतलब\b",
    r"\bयानी\b",
    r"\bजैसे कि\b",
    r"\bअरे\b",
    r"\bतो बेसिकली\b",
]

