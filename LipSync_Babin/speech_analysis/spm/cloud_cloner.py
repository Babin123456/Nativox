"""
cloud_cloner.py — Client for Expressive Cloud GPU Voice Cloning (Option 1).
Connects local LipSync Lab to the free Google Colab F5-TTS backend.
Supports both Gradio Client and FastAPI endpoints.
"""
import os
from typing import Optional

class CloudVoiceBridge:
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or os.getenv("EXPRESSIVE_BACKEND_URL", "").strip()

    def is_available(self) -> bool:
        return bool(self.endpoint_url and self.endpoint_url.startswith("http"))

    def clone_and_synthesize(self, text: str, ref_audio_path: str, output_wav_path: str, ref_text: str = "") -> str:
        if not self.is_available():
            raise ValueError("Cloud Voice Cloning backend URL is not configured.")

        # Check if URL is a Gradio share link (e.g., https://xxxx.gradio.live)
        if "gradio.live" in self.endpoint_url or "gradio" in self.endpoint_url:
            from gradio_client import Client, handle_file
            client = Client(self.endpoint_url)
            result = client.predict(
                ref_audio=handle_file(ref_audio_path),
                text=text,
                ref_text=ref_text,
                api_name="/predict"
            )
            # result is the filepath to the generated wav downloaded locally by gradio_client
            import shutil
            shutil.copyfile(result, output_wav_path)
            return output_wav_path
        else:
            # Fallback to standard FastAPI endpoint
            import requests
            url = f"{self.endpoint_url.rstrip('/')}/clone"
            with open(ref_audio_path, "rb") as f_audio:
                files = {"ref_audio": (os.path.basename(ref_audio_path), f_audio, "audio/wav")}
                data = {"text": text, "ref_text": ref_text}
                response = requests.post(url, files=files, data=data, timeout=180)
                response.raise_for_status()

                with open(output_wav_path, "wb") as f_out:
                    f_out.write(response.content)

            return output_wav_path
