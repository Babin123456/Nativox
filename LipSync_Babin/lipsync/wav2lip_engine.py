import os
import subprocess
import sys
from pathlib import Path

class Wav2LipEngine:
    def __init__(self, repo=None, checkpoint=None):
        self.repo = Path(repo or os.getenv("WAV2LIP_REPO"))
        self.checkpoint = Path(checkpoint or os.getenv("WAV2LIP_CHECKPOINT"))

    def generate(self, video_segment: Path, dubbed_audio: Path, output_video: Path, resize_factor: int = 2):
        if not self.repo or not self.checkpoint:
            raise RuntimeError("Configure WAV2LIP_REPO and WAV2LIP_CHECKPOINT in .env")
        if not self.repo.exists():
            raise FileNotFoundError(f"Wav2Lip repo not found at {self.repo}")
        if not self.checkpoint.exists():
            raise FileNotFoundError(f"Wav2Lip checkpoint not found at {self.checkpoint}")

        video_segment = Path(video_segment).resolve()
        dubbed_audio = Path(dubbed_audio).resolve()
        output_video = Path(output_video).resolve()

        output_video.parent.mkdir(parents=True, exist_ok=True)
        
        # Prefer the virtualenv python where torch is installed (e.g. LipSyncLab_v2 or local)
        lipsync_python = Path("C:/Users/babin/Downloads/LipSyncLab_v2/LipSync_Lab/.venv/Scripts/python.exe")
        py_exe = str(lipsync_python) if lipsync_python.exists() else sys.executable

        inference_script = self.repo / "inference.py"
        cmd = [
            py_exe,
            str(inference_script),
            "--checkpoint_path", str(self.checkpoint),
            "--face", str(video_segment),
            "--audio", str(dubbed_audio),
            "--outfile", str(output_video),
            "--resize_factor", str(resize_factor),
            "--nosmooth"
        ]

        # Run in wav2lip directory so relative imports work
        res = subprocess.run(cmd, cwd=str(self.repo), capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Wav2Lip inference failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}")

        return output_video
