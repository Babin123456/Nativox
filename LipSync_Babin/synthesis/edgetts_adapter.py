import os
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from .tts_provider import TTSProvider

EDGE_VOICES = {
    "hi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural"
    },
    "bn": {
        "female": "bn-IN-TanishaaNeural",
        "male": "bn-IN-BashkarNeural"
    }
}

class EdgeTTSAdapter(TTSProvider):
    """
    Zero-API, 100% Free Edge-TTS Provider.
    Produces high-fidelity neural speech in Hindi and Bengali with zero API keys.
    """
    def __init__(self, device: str = "cpu"):
        self.device = device

    async def _generate_async(self, text: str, output_path: str, voice: str):
        communicate = edge_tts.Communicate(text, voice)
        temp_mp3 = output_path.replace(".wav", "_temp.mp3")
        await communicate.save(temp_mp3)

        cmd = [
            "ffmpeg", "-y", "-i", temp_mp3,
            "-ar", "16000", "-ac", "1", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)

    def synthesize(self, text: str, target_lang: str, speaker_audio: str = None, output_path: str = None, gender: str = None) -> str:
        if not output_path:
            output_path = "work/edge_dubbed.wav"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Auto-detect speaker gender if speaker_audio reference is provided
        if not gender and speaker_audio and Path(speaker_audio).exists():
            try:
                import parselmouth
                import numpy as np
                sound = parselmouth.Sound(str(speaker_audio))
                pitch = sound.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
                voiced = pitch.selected_array['frequency']
                voiced = voiced[voiced > 0]
                if len(voiced) > 0:
                    med_f0 = float(np.median(voiced))
                    gender = "female" if med_f0 > 165.0 else "male"
                else:
                    gender = "male"
            except Exception:
                gender = "male"
        elif not gender:
            gender = "male"

        lang_voices = EDGE_VOICES.get(target_lang, EDGE_VOICES["hi"])
        voice = lang_voices.get(gender.lower(), lang_voices["male"])

        print(f"[EdgeTTS] (Zero-API) Synthesizing text into {target_lang} ({gender}) using voice '{voice}'...")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(asyncio.run, self._generate_async(text, str(output_path), voice)).result()
        else:
            asyncio.run(self._generate_async(text, str(output_path), voice))
        return str(output_path)
