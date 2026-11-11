import os
import subprocess
from pathlib import Path

class ToneTransferBridge:
    """Morphs synthetic TTS audio to match the original speaker's vocal timbre, formant resonance, and tonal pitch."""
    def __init__(self):
        self.lipsync_python = Path(os.getenv("LIPSYNC_PYTHON", "C:/Users/babin/Downloads/LipSyncLab_v2/LipSync_Lab/.venv/Scripts/python.exe"))

    def transfer_speaker_voice(self, synthesized_audio: Path, reference_speech_audio: Path, output_audio: Path, emotional_intensity: float = 1.35):
        synthesized_audio = Path(synthesized_audio).resolve()
        reference_speech_audio = Path(reference_speech_audio).resolve()
        output_audio = Path(output_audio).resolve()

        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, r'C:\\Users\\babin\\Downloads\\LipSyncLab_v2\\LipSync_Lab')
from Pipeline2.spm.tone_transfer import ToneTransferEngine

engine = ToneTransferEngine()
engine.transfer_tone(
    synthesized_audio_path=r'{synthesized_audio}',
    reference_audio_path=r'{reference_speech_audio}',
    output_audio_path=r'{output_audio}',
    emotional_intensity={emotional_intensity}
)
print('TONE_TRANSFER_SUCCESS')
"""
        res = subprocess.run([str(self.lipsync_python), "-c", script], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[Warning] Tone transfer notice: {res.stderr}")
            # fallback to synthesized if tone transfer fails
            import shutil
            shutil.copy2(synthesized_audio, output_audio)
        return output_audio
