"""
run_dub_lipsync.py - Production-Grade Multilingual Lip-Sync Pipeline for Nativox Dubbed Output.

This pipeline bridges the output of Dubbing/00_Auto_Pip and the complete lip-sync engine of LipSync_Babin:
- Executes Wav2Lip GAN neural lip-synchronization driven by the translated dubbed speech track.
- Restores high-definition facial and lip detail, crisp teeth, and authentic mouth texture using GFPGAN.
- Employs LipSync_Babin's SelectiveCompositor with dense 468 MediaPipe facial landmarks and sub-nasal bounding:
  composites ONLY the mouth articulation onto the pristine original video.
- Preserves 100% untouched original video background, eyes, forehead, hair, and scene lighting.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LIPSYNC_DIR = WORKSPACE_ROOT / "LipSync_Babin"

if str(LIPSYNC_DIR) not in sys.path:
    sys.path.insert(0, str(LIPSYNC_DIR))

from lipsync.wav2lip_engine import Wav2LipEngine
from lipsync.face_enhancer import FaceEnhancer


def run_pipeline(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    resize_factor: int = 1,
    restore_gfpgan: bool = True,
) -> Path:
    video_path = Path(video_path).resolve()
    audio_path = Path(audio_path).resolve()
    output_path = Path(output_path).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Dubbed audio not found: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / f"temp_{output_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    wav2lip_raw = temp_dir / "wav2lip_raw.mp4"

    print(f"\n=======================================================")
    print(f"[Nativox LipSync] Running Stage 1: Wav2Lip Neural Articulation")
    print(f"  Source Video: {video_path}")
    print(f"  Dubbed Audio: {audio_path}")
    print(f"=======================================================")

    wav2lip = Wav2LipEngine()
    wav2lip.generate(
        video_segment=video_path,
        dubbed_audio=audio_path,
        output_video=wav2lip_raw,
        resize_factor=resize_factor,
    )

    if not wav2lip_raw.exists():
        raise RuntimeError("Wav2Lip failed to produce raw synthesized output.")

    print(f"\n=======================================================")
    print(f"[Nativox LipSync] Running Stage 2: GFPGAN HD Restoration & Sub-Nasal Selective Compositing")
    print(f"  Restoring teeth, lip crispness & blending onto pristine camera frames")
    print(f"=======================================================")

    enhancer = FaceEnhancer(upscale=1)
    enhancer.enhance_video(
        input_video_path=str(wav2lip_raw),
        output_video_path=str(output_path),
        original_source_video_path=str(video_path),
        audio_path=str(audio_path),
        restore_gfpgan=restore_gfpgan,
    )

    # Cleanup temporary intermediates
    if wav2lip_raw.exists():
        wav2lip_raw.unlink()
    try:
        temp_dir.rmdir()
    except Exception:
        pass

    print(f"\n[Nativox LipSync] High-Fidelity Lip-Synced Video Rendered Successfully!")
    print(f"Destination: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Production Multilingual Lip-Sync Pipeline for Nativox Dubbed Output"
    )
    parser.add_argument(
        "--job-dir",
        type=str,
        default=None,
        help="Path to Dubbing/00_Auto_Pip job directory",
    )
    parser.add_argument("--video", type=str, default=None, help="Path to original input video")
    parser.add_argument("--audio", type=str, default=None, help="Path to dubbed audio track (.wav or .mp3)")
    parser.add_argument("--output", type=str, default=None, help="Destination path for final lipsynced video")
    parser.add_argument(
        "--resize-factor",
        type=int,
        default=1,
        help="Resize factor for Wav2Lip (1 = full native resolution, 2 = half for speed)",
    )
    parser.add_argument(
        "--no-gfpgan",
        action="store_true",
        help="Disable GFPGAN neural face restoration (not recommended)",
    )

    args = parser.parse_args()

    default_outputs_dir = Path(__file__).resolve().parent / "outputs"
    default_outputs_dir.mkdir(parents=True, exist_ok=True)

    if args.job_dir:
        job_path = Path(args.job_dir).resolve()
        if not job_path.exists():
            raise FileNotFoundError(f"Job directory not found: {job_path}")

        video_path = job_path / "input_video.mp4"
        audio_path = job_path / "dubbed_audio.wav"
        if not audio_path.exists():
            audio_path = job_path / "dubbed_audio.mp3"

        out_path = Path(args.output).resolve() if args.output else (default_outputs_dir / f"{job_path.name}_lipsynced.mp4")
    else:
        if not args.video or not args.audio:
            raise ValueError("Either --job-dir OR both --video and --audio must be supplied.")
        video_path = Path(args.video).resolve()
        audio_path = Path(args.audio).resolve()
        out_path = Path(args.output).resolve() if args.output else (default_outputs_dir / f"{video_path.stem}_lipsynced.mp4")

    run_pipeline(
        video_path=video_path,
        audio_path=audio_path,
        output_path=out_path,
        resize_factor=args.resize_factor,
        restore_gfpgan=not args.no_gfpgan,
    )


if __name__ == "__main__":
    main()
