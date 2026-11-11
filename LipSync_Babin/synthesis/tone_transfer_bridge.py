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

    def transfer_speaker_voice(self, synthesized_audio: Path, reference_speech_audio: Path, output_audio: Path, emotional_intensity: float = 1.35, base_speaker_name: str = "hi-IN-MadhurNeural"):
        synthesized_audio = Path(synthesized_audio).resolve()
        reference_speech_audio = Path(reference_speech_audio).resolve()
        output_audio = Path(output_audio).resolve()

        # 1. Primary: Use Neural OpenVoice V2 Tone Color Converter for actual voice identity transfer
        root_dir = Path(__file__).resolve().parent.parent
        openvoice_script = f"""
import sys, os
from pathlib import Path

openvoice_repo = Path(r'C:/Users/babin/Downloads/LipSyncLab_v2/LipSync_Lab/Pipeline2/models/openvoice/OpenVoice')
if openvoice_repo.exists():
    sys.path.insert(0, str(openvoice_repo))
sys.path.insert(0, r'{root_dir}')
sys.path.insert(0, r'C:/Users/babin/Downloads/LipSyncLab_v2/LipSync_Lab')

from speech_analysis.spm.openvoice_converter import OpenVoiceConverter
converter = OpenVoiceConverter(device='cpu')
converter.convert_voice(
    base_tts_audio_path=r'{synthesized_audio}',
    reference_media_path=r'{reference_speech_audio}',
    output_audio_path=r'{output_audio}',
    base_speaker_name='{base_speaker_name}',
    tau=0.15
)
print('OPENVOICE_SUCCESS')
"""
        res = subprocess.run([str(self.lipsync_python), "-c", openvoice_script], capture_output=True, text=True)
        if res.returncode == 0 and "OPENVOICE_SUCCESS" in res.stdout:
            print("[ToneTransfer] Neural OpenVoice V2 speaker voice conversion complete.")
            return output_audio

        print(f"[Warning] OpenVoice V2 fell back ({res.stderr[:200] if res.stderr else 'no output'}), using Praat PSOLA...")

        # 2. Secondary Fallback: Praat PSOLA formant and pitch shifting
        try:
            from speech_analysis.spm.tone_transfer import ToneTransferEngine
            engine = ToneTransferEngine()
            engine.transfer_tone(
                synthesized_audio_path=str(synthesized_audio),
                reference_audio_path=str(reference_speech_audio),
                output_audio_path=str(output_audio),
                emotional_intensity=emotional_intensity
            )
            print("[ToneTransfer] Praat PSOLA speaker tone transfer complete.")
            return output_audio
        except Exception:
            pass

        # 3. Last-resort copy
        import shutil
        shutil.copy2(synthesized_audio, output_audio)
        return output_audio
