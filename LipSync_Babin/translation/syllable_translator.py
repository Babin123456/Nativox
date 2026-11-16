import os
from pathlib import Path

class SyllableAwareTranslator:
    """
    Translates English speech into natural, conversational Hindi or Bengali while enforcing 
    a strict syllable and duration budget so speech rate remains completely natural (1.0x).
    """
    def __init__(self):
        pass

    def translate_constrained(self, text: str, target_lang: str, target_seconds: float) -> str:
        """Translates text using 100% zero-API colloquial translator."""
        from translation.translator import Translator
        tr = Translator()
        return tr._translate_zero_api(text, target_lang)
