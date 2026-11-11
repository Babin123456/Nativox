import os
import subprocess
from pathlib import Path

class StemSeparatorBridge:
    """Separates human speech and background music/ambience using Demucs."""
    def __init__(self):
        self.lipsync_python = Path("C:/Users/babin/Downloads/LipSyncLab_v2/LipSync_Lab/.venv/Scripts/python.exe")

    def separate(self, media_path: Path, output_dir: Path):
        media_path = Path(media_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        vocals_path = output_dir / f"{media_path.stem}_vocals.wav"
        bgm_path = output_dir / f"{media_path.stem}_bgm.wav"

        if vocals_path.exists() and bgm_path.exists():
            return vocals_path, bgm_path

        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, r'C:\\Users\\babin\\Downloads\\LipSyncLab_v2\\LipSync_Lab')
from Pipeline2.audio_separator import AudioStemSeparator

sep = AudioStemSeparator()
voc, bgm = sep.separate(r'{media_path}', r'{output_dir}')
print(f'SEPARATED:{{voc}}|{{bgm}}')
"""
        res = subprocess.run([str(self.lipsync_python), "-c", script], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Audio stem separation failed: {res.stderr}\n{res.stdout}")

        # Rename to clean filenames
        for line in res.stdout.splitlines():
            if line.startswith("SEPARATED:"):
                v_res, b_res = line.replace("SEPARATED:", "").split("|")
                Path(v_res).replace(vocals_path)
                Path(b_res).replace(bgm_path)
                break

        return vocals_path, bgm_path
