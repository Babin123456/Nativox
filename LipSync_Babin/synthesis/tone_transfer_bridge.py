import os
import sys
import subprocess
from pathlib import Path
from utils.env_utils import get_python_executable

class ToneTransferBridge:
    """Morphs synthetic TTS audio to match the original speaker's vocal timbre, formant resonance, and tonal pitch."""
    def __init__(self):
        self.lipsync_python = get_python_executable()

    def transfer_speaker_voice(self, synthesized_audio: Path, reference_speech_audio: Path, output_audio: Path, emotional_intensity: float = 1.35, base_speaker_name: str = "hi-IN-MadhurNeural"):
        synthesized_audio = Path(synthesized_audio).resolve()
        reference_speech_audio = Path(reference_speech_audio).resolve()
        output_audio = Path(output_audio).resolve()

        # 1. Primary: Use Neural OpenVoice V2 Tone Color Converter for actual voice identity transfer
        root_dir = Path(__file__).resolve().parent.parent
        custom_pipeline_dir = os.getenv("PIPELINE2_DIR", "")
        custom_openvoice_repo = os.getenv("OPENVOICE_REPO", "")

        openvoice_script = f"""
import sys, os
from pathlib import Path

root_dir = Path(r'{root_dir}')
pipeline2_dir = Path(r'{custom_pipeline_dir}') if r'{custom_pipeline_dir}' else None
openvoice_custom = Path(r'{custom_openvoice_repo}') if r'{custom_openvoice_repo}' else None

cand_openvoice_repos = [
    openvoice_custom,
    root_dir / "models" / "openvoice" / "OpenVoice",
    root_dir / "Pipeline2" / "models" / "openvoice" / "OpenVoice"
]
for p in filter(None, cand_openvoice_repos):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

cand_sys_dirs = [
    pipeline2_dir,
    root_dir,
    root_dir / "Pipeline2"
]
for d in filter(None, cand_sys_dirs):
    if d.exists() and str(d) not in sys.path:
        sys.path.insert(0, str(d))

try:
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
except Exception as e:
    print(f'OpenVoice error: {{e}}')
"""
        res = subprocess.run([str(self.lipsync_python), "-c", openvoice_script], capture_output=True, text=True)
        if res.returncode == 0 and "OPENVOICE_SUCCESS" in res.stdout and output_audio.exists() and output_audio.stat().st_size > 0:
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
