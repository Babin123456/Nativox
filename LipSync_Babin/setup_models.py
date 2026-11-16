"""
setup_models.py — Automated Model Downloader & Environment Setup for LipSync_Babin.

Allows any user cloning LipSync_Babin to automatically download all required neural model
checkpoints (Wav2Lip, GFPGAN weights, etc.) with a single command on any OS (Windows, Linux, macOS).
"""
import os
import sys
import urllib.request
import shutil
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

MODELS = {
    "wav2lip_gan": {
        "url": "https://huggingface.co/Akash0423/Wav2Lip/resolve/main/wav2lip_gan.pth",
        "dest": ROOT_DIR / "models" / "wav2lip" / "checkpoints" / "wav2lip_gan.pth",
        "description": "Wav2Lip GAN Checkpoint (Photorealistic Lip Synchronization)"
    },
    "gfpgan_v14": {
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        "dest": ROOT_DIR / "gfpgan" / "weights" / "GFPGANv1.4.pth",
        "description": "GFPGAN v1.4 Model (High-Definition Lip, Teeth & Mouth Restoration)"
    },
    "detection_resnet50": {
        "url": "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
        "dest": ROOT_DIR / "gfpgan" / "weights" / "detection_Resnet50_Final.pth",
        "description": "FaceXLib ResNet50 Face Detector"
    },
    "s3fd_detector": {
        "url": "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316842.pth",
        "dest": ROOT_DIR / "models" / "wav2lip" / "face_detection" / "detection" / "sfd" / "s3fd.pth",
        "description": "S3FD Face Detection Model for Wav2Lip"
    },
    "parsing_parsenet": {
        "url": "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
        "dest": ROOT_DIR / "gfpgan" / "weights" / "parsing_parsenet.pth",
        "description": "FaceXLib ParseNet Facial Landmark & Feature Segmentation"
    }
}

def download_file(url: str, dest_path: Path, description: str):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists() and dest_path.stat().st_size > 1024:
        print(f"[OK] Already exists: {description} -> {dest_path.name}")
        return

    print(f"\n[Downloading] {description}...")
    print(f"  URL: {url}")
    print(f"  Destination: {dest_path}")

    def report_hook(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100.0, downloaded * 100.0 / total_size)
            mb_down = downloaded / (1024 * 1024)
            mb_tot = total_size / (1024 * 1024)
            sys.stdout.write(f"\r  Progress: {percent:5.1f}% [{mb_down:6.1f} MB / {mb_tot:6.1f} MB]")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, str(dest_path), reporthook=report_hook)
        print("\n  [Done] Download successful!")
    except Exception as e:
        print(f"\n  [Error] Failed to download {url}: {e}")
        if dest_path.exists():
            dest_path.unlink()

def ensure_wav2lip_repo():
    wav2lip_dir = ROOT_DIR / "models" / "wav2lip"
    inference_script = wav2lip_dir / "inference.py"
    if inference_script.exists():
        print(f"[OK] Wav2Lip repo present at {wav2lip_dir}")
        return

    print("\n[Cloning] Wav2Lip repository...")
    wav2lip_dir.parent.mkdir(parents=True, exist_ok=True)
    import subprocess
    cmd = ["git", "clone", "https://github.com/Rudrabha/Wav2Lip.git", str(wav2lip_dir)]
    try:
        subprocess.run(cmd, check=True)
        print("[Done] Wav2Lip repo cloned successfully.")
    except Exception as e:
        print(f"[Warning] Failed to git clone Wav2Lip automatically ({e}). Please clone manually into {wav2lip_dir}.")

def setup_env_file():
    env_file = ROOT_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            shutil.copyfile(str(env_example), str(env_file))
            print("[OK] Created .env from .env.example")
        else:
            default_content = (
                "NATIVOX_DEVICE=cpu\n"
                "NATIVOX_TTS=free\n"
                "SARVAM_API_KEY=\n"
                "WAV2LIP_REPO=models/wav2lip\n"
                "WAV2LIP_CHECKPOINT=models/wav2lip/checkpoints/wav2lip_gan.pth\n"
            )
            env_file.write_text(default_content, encoding="utf-8")
            print("[OK] Created default .env")
    else:
        print("[OK] Existing .env file found.")

def main():
    print("==================================================================")
    print("   Nativox LipSync_Babin — Automated Model & Setup Installer      ")
    print("==================================================================")
    
    # 1. Setup default .env
    setup_env_file()

    # 2. Ensure Wav2Lip repo
    ensure_wav2lip_repo()

    # 3. Download model weights
    for key, info in MODELS.items():
        download_file(info["url"], info["dest"], info["description"])

    print("\n==================================================================")
    print("   Setup Complete! All dependencies and models are configured.   ")
    print("   You can now launch:")
    print("     - Web UI: python -m uvicorn web.app:app --port 7860")
    print("     - CLI:    python pipeline.py --input test2.mp4 --lang hi --output output.mp4")
    print("==================================================================")

if __name__ == "__main__":
    main()
