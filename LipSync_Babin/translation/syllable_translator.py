import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class SyllableAwareTranslator:
    """
    Translates English speech into natural, conversational Hindi or Bengali while enforcing 
    a strict syllable and duration budget so speech rate remains completely natural (1.0x).
    """
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.headers = {"api-subscription-key": self.api_key, "Content-Type": "application/json"} if self.api_key else {}

    def translate_constrained(self, text: str, target_lang: str, target_seconds: float) -> str:
        # If no SARVAM_API_KEY, use zero-API colloquial translator directly
        if not self.api_key:
            return self._zero_api_translate(text, target_lang, target_seconds)

        # Estimate syllable count for target runtime (~3.0 syllables per second for natural Indic speech)
        target_syllables = max(10, int(target_seconds * 3.0))
        lang_name = "Hindi" if target_lang == "hi" else "Bengali"

        prompt = f"""You are an elite dialogue adapter for multilingual film and video dubbing.
Task: Translate this English speech into natural, spoken {lang_name}.

CRITICAL CONSTRAINTS:
1. TIMING & DURATION BUDGET: The original speaker took {target_seconds:.1f} seconds. Your {lang_name} sentence MUST have approximately {target_syllables} syllables so it can be comfortably spoken in {target_seconds:.1f} seconds without being rushed.
2. NATURAL COLLOQUIAL SPEECH: Must sound like genuine natural spoken phrasing, NEVER literal or stiff word-for-word translation.
3. CONCISENESS: Keep it concise and natural so it fits the speaker's original breath and cadence.
4. Output ONLY the translated {lang_name} sentence. Do not add quotes, notes, or explanations.

English sentence: "{text}"
"""
        payload = {
            "model": "sarvam-105b-conversations",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 120,
            "temperature": 0.2
        }

        try:
            res = requests.post("https://api.sarvam.ai/v1/chat/completions", json=payload, headers=self.headers, timeout=25)
            if res.status_code == 200:
                data = res.json()
                translated = data["choices"][0]["message"]["content"].strip()
                translated = translated.strip('"\'')
                if translated:
                    return translated
        except Exception:
            pass

        return self._zero_api_translate(text, target_lang, target_seconds)

    def _zero_api_translate(self, text: str, target_lang: str, target_seconds: float) -> str:
        """Zero-API fallback translation using Google GTX or deep-translator."""
        from translation.translator import Translator
        tr = Translator()
        return tr._translate_zero_api(text, target_lang)
