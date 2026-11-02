"""
setup_env.py
------------
Cross-platform environment setup utility for Nativox.
Installs dependencies for all pipeline stages into the active Python environment
or creates a dedicated virtual environment.

Usage:
    python setup_env.py
    python setup_env.py --create-venv
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 11)


def check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        sys.exit(
            f"Error: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required. "
            f"Current version is {sys.version}."
        )


def find_requirements_files(root: Path) -> list[Path]:
    req_files = [
        root / "00_Auto_Pip" / "requirements.txt",
        root / "01_MP4_to_MP3" / "requirements.txt",
        root / "02_MP3_to_Text" / "requirements.txt",
        root / "03_Text_to_Keyword" / "requirements.txt",
        root / "04_Keyword_to_Sentence_Construction" / "requirements.txt",
        root / "05a_Keyword_Translation__Sagnik" / "requirements.txt",
        root / "05b_Sentence_Reformation__Atanu" / "requirements.txt",
        root / "06_Converted_Text_to_MP3" / "requirements.txt",
        root / "07_Merge_MP3_with_MP4" / "requirements.txt",
    ]
    return [p for p in req_files if p.is_file()]


def main() -> None:
    check_python_version()

    parser = argparse.ArgumentParser(
        description="Nativox cross-platform environment setup."
    )
    parser.add_argument(
        "--create-venv",
        action="store_true",
        help="Create a local virtual environment in 00_Auto_Pip/venv",
    )
    args = parser.parse_args()

    pip_dir = Path(__file__).resolve().parent
    root = pip_dir.parent

    python_bin = sys.executable

    if args.create_venv:
        venv_dir = pip_dir / "venv"
        if not venv_dir.is_dir():
            print(f"[*] Creating virtual environment in {venv_dir}...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        if os.name == "nt":
            python_bin = str(venv_dir / "Scripts" / "python.exe")
        else:
            python_bin = str(venv_dir / "bin" / "python")

    print("[*] Upgrading pip...")
    subprocess.run([python_bin, "-m", "pip", "install", "--upgrade", "pip"], check=True)

    req_files = find_requirements_files(root)
    print(f"[*] Installing dependencies across {len(req_files)} stage requirements files...")
    for req in req_files:
        stage_name = req.parent.parent.name if req.parent.name == "backend" else req.parent.name
        print(f"    -> Installing: {stage_name} ({req.name})")
        subprocess.run([python_bin, "-m", "pip", "install", "-r", str(req)], check=True)

    print("\n[+] Setup complete! You can now run the pipeline with:")
    print('    python orchestrator.py "path/to/video.mp4"')


if __name__ == "__main__":
    main()
