import os
import sys
import subprocess
from pathlib import Path

class ToneTransferBridge:
    """Morphs synthetic TTS audio to match the original speaker's vocal timbre, formant resonance, and tonal pitch."""
    def __init__(self):
        # Prefer system Python 3.11 with parselmouth, or fallback to current python
        cand_py = [
            os.getenv("LIPSYNC_PYTHON"),
            r"C:\Users\babin\AppData\Local\Programs\Python\Python311\python.exe",
            r"C:\Users\babin\Downloads\LipSyncLab_v2\LipSync_Lab\.venv\Scripts\python.exe",
            sys.executable
        ]
        self.lipsync_python = next((p for p in cand_py if p and Path(p).exists()), sys.executable)

    def transfer_speaker_voice(self, synthesized_audio: Path, reference_speech_audio: Path, output_audio: Path, emotional_intensity: float = 1.35):
        synthesized_audio = Path(synthesized_audio).resolve()
        reference_speech_audio = Path(reference_speech_audio).resolve()
        output_audio = Path(output_audio).resolve()

        # Try in-process transfer first if parselmouth is available
        try:
            from speech_analysis.spm.tone_transfer import ToneTransferEngine
            engine = ToneTransferEngine()
            engine.transfer_tone(
                synthesized_audio_path=str(synthesized_audio),
                reference_audio_path=str(reference_speech_audio),
                output_audio_path=str(output_audio),
                emotional_intensity=emotional_intensity
            )
            print("[ToneTransfer] In-process speaker tone transfer complete.")
            return output_audio
        except Exception as e:
            pass

        # Subprocess transfer
        root_dir = Path(__file__).resolve().parent.parent
        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, r'{root_dir}')
sys.path.insert(0, r'C:\\Users\\babin\\Downloads\\LipSyncLab_v2\\LipSync_Lab')

try:
    from speech_analysis.spm.tone_transfer import ToneTransferEngine
    engine = ToneTransferEngine()
except ImportError:
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
            import shutil
            shutil.copy2(synthesized_audio, output_audio)
        else:
            print("[ToneTransfer] Subprocess speaker tone transfer complete.")
        return output_audio
