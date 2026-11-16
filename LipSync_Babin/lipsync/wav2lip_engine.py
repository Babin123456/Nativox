import os
import subprocess
import sys
from pathlib import Path
from utils.env_utils import get_python_executable

class Wav2LipEngine:
    def __init__(self, repo=None, checkpoint=None):
        root_dir = Path(__file__).resolve().parent.parent
        default_repo = root_dir / "models" / "wav2lip"
        default_ckpt = root_dir / "models" / "wav2lip" / "checkpoints" / "wav2lip_gan.pth"

        raw_repo = repo or os.getenv("WAV2LIP_REPO") or (str(default_repo) if default_repo.exists() else None)
        raw_checkpoint = checkpoint or os.getenv("WAV2LIP_CHECKPOINT") or (str(default_ckpt) if default_ckpt.exists() else None)

        self.repo = Path(raw_repo) if raw_repo else None
        self.checkpoint = Path(raw_checkpoint) if raw_checkpoint else None

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
        
        # Discover python executable dynamically across any device/OS
        py_exe = get_python_executable()

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
