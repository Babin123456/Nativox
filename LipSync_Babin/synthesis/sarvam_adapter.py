import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv
from .tts_provider import TTSProvider

load_dotenv()

class SarvamAdapter(TTSProvider):
    def __init__(self, device="cpu"):
        self.api_key = os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise RuntimeError("Set SARVAM_API_KEY before using this adapter.")
        self.device = device
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

    def synthesize(self, text: str, reference_audio: Path = None, prosody: dict = None, target_lang: str = "hi", output_path: Path = None) -> Path:
        """Synthesize target language speech using Sarvam Bulbul TTS API."""
        url = "https://api.sarvam.ai/text-to-speech"
        lang_code = "hi-IN" if target_lang == "hi" else "bn-IN"
        
        # Pick default speaker for language (compatible with bulbul:v3)
        speaker = "aditya"
        if prosody and prosody.get("speaker"):
            speaker = prosody["speaker"]

        payload = {
            "inputs": [text],
            "target_language_code": lang_code,
            "speaker": speaker,
            "model": "bulbul:v3"
        }

        res = requests.post(url, json=payload, headers=self.headers)
        if res.status_code != 200:
            raise RuntimeError(f"Sarvam TTS failed ({res.status_code}): {res.text}")

        data = res.json()
        audios = data.get("audios", [])
        if not audios:
            raise RuntimeError("Sarvam TTS returned empty audio list.")

        audio_bytes = base64.b64decode(audios[0])

        if output_path is None:
            output_path = Path("work") / f"synth_{target_lang}.wav"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        return output_path
