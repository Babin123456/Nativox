"""
run_dub_lipsync.py - Lightweight Selective Lip-Sync Pipeline for Nativox Dubbed Output.

This pipeline bridges the output of Dubbing/00_Auto_Pip and the lip-sync engine of LipSync_Babin:
- Bypasses Whisper, Demucs, Translation, and TTS (saves massive compute & memory).
- Runs Wav2Lip (using checkpoints from LipSync_Babin/models/wav2lip) to synthesize realistic mouth articulation.
- Uses SelectiveCompositor (with MediaPipe dense facial landmarks) to composite ONLY the sub-nasal mouth region.
- Preserves 100% untouched original video background, eyes, nose, forehead, hair, and scene lighting.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import cv2
import numpy as np

# Ensure LipSync_Babin is discoverable for importing models and utilities if needed
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LIPSYNC_DIR = WORKSPACE_ROOT / "LipSync_Babin"

if str(LIPSYNC_DIR) not in sys.path:
    sys.path.insert(0, str(LIPSYNC_DIR))

try:
    import mediapipe as mp
    _HAS_MEDIAPIPE = True
except ImportError:
    _HAS_MEDIAPIPE = False


class LandmarkMouthMasker:
    """
    Generates a temporally stable, anatomically bounded mouth-region mask in [0.0, 1.0].
    Strictly cuts off everything above the subnasale (philtrum top) so nose, eyes,
    eyebrows, forehead, hair, and background remain 100% untouched camera pixels.
    """

    def __init__(self, smooth_alpha: float = 0.7):
        self.smooth_alpha = smooth_alpha
        self.prev_ellipse_params: Optional[Tuple[float, float, float, float]] = None
        self.prev_subnasal_y: Optional[float] = None
        self.face_mesh = None

        if _HAS_MEDIAPIPE:
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

    def close(self):
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None

    def reset_temporal_state(self):
        self.prev_ellipse_params = None
        self.prev_subnasal_y = None

    def create_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        h, w = frame_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)

        if self.face_mesh is None:
            return mask

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return mask

        landmarks = results.multi_face_landmarks[0].landmark
        lm_pts = np.array([(p.x * w, p.y * h) for p in landmarks], dtype=np.float32)

        subnasale = lm_pts[164] if len(lm_pts) > 164 else lm_pts[2]
        mouth_l = lm_pts[61]
        mouth_r = lm_pts[291]
        mouth_top = lm_pts[0]
        mouth_bot = lm_pts[17]
        chin = lm_pts[152] if len(lm_pts) > 152 else (mouth_bot + np.array([0, 30.0]))

        # Sub-nasal cutoff line (strictly below nose base and nostrils)
        curr_subnasal_y = float(subnasale[1] + 0.15 * (mouth_top[1] - subnasale[1]))

        # Mouth geometry
        mouth_center_x = float((mouth_l[0] + mouth_r[0]) / 2.0)
        mouth_center_y = float((mouth_top[1] + mouth_bot[1]) / 2.0)
        mouth_width = float(np.linalg.norm(mouth_r - mouth_l))
        chin_y = float(chin[1])

        curr_cx = mouth_center_x
        curr_cy = (mouth_center_y + chin_y) / 2.0
        curr_rx = max(mouth_width * 0.75, 20.0)
        curr_ry = max((chin_y - curr_subnasal_y) / 2.0, mouth_width * 0.45)

        # Temporal Smoothing (EMA)
        if self.prev_ellipse_params is not None:
            a = self.smooth_alpha
            cx = a * curr_cx + (1 - a) * self.prev_ellipse_params[0]
            cy = a * curr_cy + (1 - a) * self.prev_ellipse_params[1]
            rx = a * curr_rx + (1 - a) * self.prev_ellipse_params[2]
            ry = a * curr_ry + (1 - a) * self.prev_ellipse_params[3]
            subnasal_y = a * curr_subnasal_y + (1 - a) * (self.prev_subnasal_y or curr_subnasal_y)
        else:
            cx, cy, rx, ry = curr_cx, curr_cy, curr_rx, curr_ry
            subnasal_y = curr_subnasal_y

        self.prev_ellipse_params = (cx, cy, rx, ry)
        self.prev_subnasal_y = subnasal_y

        # Draw Mouth/Jaw Anatomical Mask
        cv2.ellipse(
            mask,
            (int(round(cx)), int(round(cy))),
            (int(round(rx)), int(round(ry))),
            0,
            0,
            360,
            1.0,
            -1,
        )

        # Strict Sub-Nasal Zeroing: pixels above cutoff are zeroed out
        cutoff_idx = max(0, min(h - 1, int(round(subnasal_y))))
        mask[:cutoff_idx, :] = 0.0

        # Dual Gaussian Feathering
        kernel_size = int(max(31, round(rx * 0.4))) | 1
        feathered = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)

        # Bleed guard
        bleed_guard_idx = max(0, cutoff_idx - int(kernel_size * 0.5))
        feathered[:bleed_guard_idx, :] = 0.0

        return np.clip(feathered, 0.0, 1.0)


class SelectiveCompositor:
    """
    Blends the Wav2Lip synthesized mouth onto original frames using the sub-nasal mask.
    """

    def __init__(self, smooth_alpha: float = 0.7):
        self.masker = LandmarkMouthMasker(smooth_alpha=smooth_alpha)

    def composite_video(
        self,
        orig_video_path: Path,
        gen_video_path: Path,
        audio_path: Path,
        output_video_path: Path,
    ) -> Dict[str, Any]:
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        print("[SelectiveCompositor] Starting sub-nasal mouth compositing...")

        cap_orig = cv2.VideoCapture(str(orig_video_path))
        cap_gen = cv2.VideoCapture(str(gen_video_path))

        fps = cap_orig.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap_orig.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap_orig.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))

        temp_avi = str(output_video_path.with_name(f"{output_video_path.stem}_temp.avi"))
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        out = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))

        self.masker.reset_temporal_state()
        frame_idx = 0

        while cap_orig.isOpened():
            ret_orig, frame_orig = cap_orig.read()
            if not ret_orig:
                break

            ret_gen, frame_gen = cap_gen.read()
            if not ret_gen:
                frame_gen = frame_orig

            # Match dimension if generated frame differs
            if frame_gen.shape[:2] != (height, width):
                gen_resized = cv2.resize(frame_gen, (width, height), interpolation=cv2.INTER_LANCZOS4)
            else:
                gen_resized = frame_gen

            # Generate sub-nasal mouth mask
            mask = self.masker.create_mask(frame_orig)
            mask_3c = np.repeat(mask[:, :, np.newaxis], 3, axis=2)

            # Alpha blend only on the mouth area
            blended = (1.0 - mask_3c) * frame_orig.astype(np.float32) + mask_3c * gen_resized.astype(np.float32)
            out_frame = np.clip(np.round(blended), 0.0, 255.0).astype(np.uint8)

            out.write(out_frame)
            frame_idx += 1

            if frame_idx % 30 == 0 or frame_idx == total_frames:
                print(f"  Composited {frame_idx}/{total_frames} frames...", flush=True)

        cap_orig.release()
        cap_gen.release()
        out.release()
        self.masker.close()

        # Mux with dubbed audio track using visually lossless x264 CRF 17
        print("[SelectiveCompositor] Muxing composited video with dubbed audio...")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            temp_avi,
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_video_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            if Path(temp_avi).exists():
                Path(temp_avi).unlink()
            raise RuntimeError(f"FFmpeg muxing failed:\n{res.stderr}")

        if Path(temp_avi).exists():
            Path(temp_avi).unlink()

        return {
            "total_frames": frame_idx,
            "output_path": str(output_video_path),
        }


def run_wav2lip(
    video_path: Path,
    audio_path: Path,
    output_wav2lip_path: Path,
    python_exe: str,
    resize_factor: int = 1,
) -> Path:
    """Runs Wav2Lip neural lip synthesis."""
    wav2lip_repo = LIPSYNC_DIR / "models" / "wav2lip"
    ckpt_path = wav2lip_repo / "checkpoints" / "wav2lip_gan.pth"

    if not ckpt_path.exists():
        ckpt_path = wav2lip_repo / "checkpoints" / "wav2lip.pth"

    if not ckpt_path.exists():
        raise FileNotFoundError(f"Wav2Lip checkpoint not found under {wav2lip_repo / 'checkpoints'}")

    inference_script = wav2lip_repo / "inference.py"
    output_wav2lip_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Wav2Lip] Running inference with {ckpt_path.name}...")
    cmd = [
        python_exe,
        str(inference_script),
        "--checkpoint_path",
        str(ckpt_path),
        "--face",
        str(video_path.resolve()),
        "--audio",
        str(audio_path.resolve()),
        "--outfile",
        str(output_wav2lip_path.resolve()),
        "--resize_factor",
        str(resize_factor),
        "--nosmooth",
    ]

    res = subprocess.run(cmd, cwd=str(wav2lip_repo), capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Wav2Lip inference failed with code {res.returncode}:\n{res.stderr}\n{res.stdout}")

    return output_wav2lip_path


def main():
    parser = argparse.ArgumentParser(
        description="Fast standalone selective lip-sync pipeline for dubbed video/audio"
    )
    parser.add_argument(
        "--job-dir",
        type=str,
        default=None,
        help="Path to Dubbing/00_Auto_Pip job directory (e.g. Dubbing/00_Auto_Pip/jobs/job_1156f651)",
    )
    parser.add_argument("--video", type=str, default=None, help="Path to original input video")
    parser.add_argument("--audio", type=str, default=None, help="Path to dubbed audio track (.wav or .mp3)")
    parser.add_argument("--output", type=str, default=None, help="Destination path for final lipsynced video")
    parser.add_argument(
        "--resize-factor",
        type=int,
        default=1,
        help="Resize factor for Wav2Lip (1 = full resolution, 2 = half resolution for speed)",
    )

    args = parser.parse_args()

    # Default output destination is Dub_with_LipSync/outputs/
    default_outputs_dir = Path(__file__).resolve().parent / "outputs"
    default_outputs_dir.mkdir(parents=True, exist_ok=True)

    # Resolve input paths
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

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"=== Dub_with_LipSync Pipeline ===")
    print(f"Video: {video_path}")
    print(f"Audio: {audio_path}")
    print(f"Target Output: {out_path}")

    # Use the dedicated virtual environment of LipSync_Babin
    python_exe = str(LIPSYNC_DIR / ".venv" / "Scripts" / "python.exe")
    if not Path(python_exe).exists():
        python_exe = sys.executable

    temp_dir = out_path.parent / "temp_lipsync"
    temp_dir.mkdir(parents=True, exist_ok=True)
    wav2lip_raw_output = temp_dir / "wav2lip_raw.mp4"

    # Step 1: Wav2Lip neural synthesis
    run_wav2lip(
        video_path=video_path,
        audio_path=audio_path,
        output_wav2lip_path=wav2lip_raw_output,
        python_exe=python_exe,
        resize_factor=args.resize_factor,
    )

    # Step 2: Selective sub-nasal compositing
    compositor = SelectiveCompositor()
    stats = compositor.composite_video(
        orig_video_path=video_path,
        gen_video_path=wav2lip_raw_output,
        audio_path=audio_path,
        output_video_path=out_path,
    )

    # Cleanup temp
    if wav2lip_raw_output.exists():
        wav2lip_raw_output.unlink()
    try:
        temp_dir.rmdir()
    except Exception:
        pass

    print(f"\n[Dub_with_LipSync] Processing finished successfully!")
    print(f"Final output video: {out_path}")
    print(f"Compositing statistics: {stats}")


if __name__ == "__main__":
    main()
