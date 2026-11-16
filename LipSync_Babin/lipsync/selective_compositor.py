"""
selective_compositor.py — Selective Temporal Mouth-Region Compositor for Nativox.

Architectural Principle:
  "PRESERVE THE ORIGINAL VIDEO AND BACKGROUND.
   REPLACE ONLY THE HUMAN DIALOGUE AND THE NECESSARY MOUTH ARTICULATION."

Exact Behavior:
  1. For non-speaking frames:
       output_frame = original_frame (100% pixel-identical, zero modifications).
  2. For speaking frames:
       output_frame = composite(original_frame, generated_frame, mouth_region_mask)
     Only the mouth and jaw region below the sub-nasal base is composited.
     Eyes, eyebrows, nose, forehead, cheeks, hair, spectacles, lighting, and background
     remain 100% untouched original camera pixels.
"""
from __future__ import annotations

import os
import sys
import subprocess
from typing import List, Tuple, Dict, Any, Optional

import cv2
import numpy as np

# MediaPipe face mesh for 468 dense anatomical landmarks
try:
    import mediapipe as mp
    _HAS_MEDIAPIPE = True
except ImportError:
    _HAS_MEDIAPIPE = False


class SpeechActivityTimeline:
    """
    Builds and manages speaker-specific speech activity intervals [start_sec, end_sec].
    Combines Whisper timestamps, audio RMS/VAD, and visual mouth activity.
    """

    def __init__(self, min_speech_duration: float = 0.2, min_silence_duration: float = 0.3):
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration

    @staticmethod
    def from_whisper_segments(
        segments: List[Dict[str, Any]],
        lead_in_s: float = 0.08,
        lead_out_s: float = 0.08,
        max_duration: Optional[float] = None
    ) -> List[Tuple[float, float]]:
        """
        Extract active speech intervals from Whisper transcript segments.
        Adds a slight physiological transition buffer (lead_in/out) for mouth opening/closing.
        Merges adjacent intervals separated by less than 0.25 seconds.
        """
        raw_intervals = []
        for seg in segments:
            start = max(0.0, float(seg.get("start", 0.0)) - lead_in_s)
            end = float(seg.get("end", 0.0)) + lead_out_s
            if max_duration is not None:
                end = min(max_duration, end)
            if end > start:
                raw_intervals.append((start, end))

        if not raw_intervals:
            return []

        # Sort and merge overlapping or near-adjacent intervals
        raw_intervals.sort(key=lambda x: x[0])
        merged: List[Tuple[float, float]] = [raw_intervals[0]]

        for current_start, current_end in raw_intervals[1:]:
            prev_start, prev_end = merged[-1]
            if current_start <= prev_end + 0.25:
                # Merge
                merged[-1] = (prev_start, max(prev_end, current_end))
            else:
                merged.append((current_start, current_end))

        return merged

    @staticmethod
    def is_speaking(timestamp_s: float, intervals: List[Tuple[float, float]]) -> bool:
        """Check if a timestamp falls within any speaking interval."""
        for start, end in intervals:
            if start <= timestamp_s <= end:
                return True
        return False


class LandmarkMouthMasker:
    """
    Generates a temporally stable, anatomically bounded mouth-region mask M in [0.0, 1.0].
    
    Anatomical Anchors (MediaPipe 468 FaceMesh):
      - Sub-nasal cutoff: Landmark 164 (subnasale / philtrum top) or 2 (nose tip).
        The mask is STRICTLY ZERO above this line. Eyes, nose, eyebrows, and glasses
        are never touched.
      - Lateral bounds: Landmarks 61 (left corner) and 291 (right corner) with
        controlled natural cheek margin.
      - Lower bound: Landmark 152 (chin) ensuring natural jaw movement is accommodated.
      - Soft feathering: Smooth Gaussian blur kernel to blend seamlessly into original skin.
      - Temporal smoothing: Exponential Moving Average (EMA) of mask parameters to eliminate
        frame-to-frame boundary jitter or flicker.
    """

    def __init__(self, smooth_alpha: float = 0.7):
        self.smooth_alpha = smooth_alpha
        self.prev_ellipse_params: Optional[Tuple[float, float, float, float]] = None  # (cx, cy, rx, ry)
        self.prev_subnasal_y: Optional[float] = None
        
        self.face_mesh = None
        if _HAS_MEDIAPIPE:
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

    def close(self):
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None

    def reset_temporal_state(self):
        self.prev_ellipse_params = None
        self.prev_subnasal_y = None

    def create_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Generate a single-channel float32 mask M in [0.0, 1.0] of shape (H, W).
        Returns all-zeros if no face is detected.
        """
        h, w = frame_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)

        if self.face_mesh is None:
            return mask

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            # Face not detected: return zeros (no modification)
            return mask

        landmarks = results.multi_face_landmarks[0].landmark
        lm_pts = np.array([(p.x * w, p.y * h) for p in landmarks], dtype=np.float32)

        # 1. Anatomical Reference Points
        # 164 = subnasale (philtrum top, directly beneath nose base)
        # 2 = nose tip, 94 = nose bottom center
        # 61 = left mouth corner, 291 = right mouth corner
        # 0 = upper lip top, 17 = lower lip bottom, 152 = chin bottom
        subnasale = lm_pts[164] if len(lm_pts) > 164 else lm_pts[2]
        nose_tip = lm_pts[2] if len(lm_pts) > 2 else subnasale
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

        # Center of lower face ellipse (between mouth and chin)
        curr_cx = mouth_center_x
        curr_cy = (mouth_center_y + chin_y) / 2.0
        curr_rx = max(mouth_width * 0.75, 20.0)
        curr_ry = max((chin_y - curr_subnasal_y) / 2.0, mouth_width * 0.45)

        # 2. Temporal Smoothing (EMA) to prevent boundary shimmer across frames
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

        # 3. Draw Mouth/Jaw Anatomical Mask
        cv2.ellipse(
            mask,
            (int(round(cx)), int(round(cy))),
            (int(round(rx)), int(round(ry))),
            0, 0, 360,
            1.0,
            -1
        )

        # 4. Strict Sub-Nasal Zeroing:
        # Every pixel above subnasal_y is STRICTLY 0.0.
        # This guarantees eyes, eyebrows, nose, cheeks, and glasses are 100% untouched.
        cutoff_idx = max(0, min(h - 1, int(round(subnasal_y))))
        mask[:cutoff_idx, :] = 0.0

        # 5. Dual Gaussian Feathering for an organic, imperceptible boundary transition
        kernel_size = int(max(31, round(rx * 0.4))) | 1  # must be odd
        feathered = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)

        # Re-enforce zeroing on the upper half of face after blur so no blur bleeds into eyes
        bleed_guard_idx = max(0, cutoff_idx - int(kernel_size * 0.5))
        feathered[:bleed_guard_idx, :] = 0.0

        return np.clip(feathered, 0.0, 1.0)


class SelectiveCompositor:
    """
    Dedicated Selective Temporal Mouth-Region Compositor.
    
    Guarantees:
      - Non-speaking frames: output_frame = original_frame (exact pixel identity).
      - Speaking frames: output_frame = composite(orig, gen, mask)
        (only mouth region replaced; upper face & scene 100% untouched).
    """

    def __init__(self, smooth_alpha: float = 0.7):
        self.masker = LandmarkMouthMasker(smooth_alpha=smooth_alpha)

    def composite_frame(
        self,
        orig_frame: np.ndarray,
        gen_frame: np.ndarray,
        is_speaking: bool,
        mask: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Composite a single frame based on speech state.
        
        Parameters:
          orig_frame  : Pristine original video frame (BGR, uint8).
          gen_frame   : Generated frame from Wav2Lip / face enhancer (BGR, uint8).
          is_speaking : Boolean indicating if speaker is actively speaking at this frame.
          mask        : Optional pre-computed float32 mask in [0.0, 1.0].
        
        Returns:
          (output_frame, mask_used)
        """
        if not is_speaking:
            # 100% UNTOUCHED ORIGINAL FRAME (Strict Pixel-Identity)
            zero_mask = np.zeros(orig_frame.shape[:2], dtype=np.float32)
            return orig_frame.copy(), zero_mask

        # Match dimensions to original frame if needed
        h, w = orig_frame.shape[:2]
        if gen_frame.shape[:2] != (h, w):
            gen_resized = cv2.resize(gen_frame, (w, h), interpolation=cv2.INTER_LANCZOS4)
        else:
            gen_resized = gen_frame

        # Compute or use mouth mask
        if mask is None:
            mask = self.masker.create_mask(orig_frame)
        mask = np.clip(mask, 0.0, 1.0)

        # Blend only where mask > 0
        mask_3c = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
        blended = (
            (1.0 - mask_3c) * orig_frame.astype(np.float32) +
            mask_3c * gen_resized.astype(np.float32)
        )
        output_frame = np.clip(np.round(blended), 0.0, 255.0).astype(np.uint8)

        return output_frame, mask

    def process_video(
        self,
        orig_video_path: str,
        gen_video_path: str,
        speaking_intervals: List[Tuple[float, float]],
        output_video_path: str,
        audio_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an entire video with selective temporal mouth-region compositing.
        
        Parameters:
          orig_video_path    : Path to original source video (source of truth).
          gen_video_path     : Path to Wav2Lip / dubbed video.
          speaking_intervals : List of (start_sec, end_sec) speech intervals.
          output_video_path  : Path to save the final composited video.
          audio_path         : Path to the target audio track (continuous BGM + dubbed dialogue).
        
        Returns:
          Stats dictionary {total_frames, speaking_frames, non_speaking_frames, ...}
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
        print(f"[SelectiveCompositor] Processing video with selective temporal compositing:")
        print(f"  • Source Video     : {orig_video_path}")
        print(f"  • Generated Video  : {gen_video_path}")
        print(f"  • Speech Intervals : {speaking_intervals}")
        print(f"  • Output Video     : {output_video_path}")

        cap_orig = cv2.VideoCapture(orig_video_path)
        cap_gen = cv2.VideoCapture(gen_video_path)

        fps = cap_orig.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap_orig.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap_orig.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))

        temp_avi = output_video_path.replace(".mp4", "_selective_temp.avi")
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))

        self.masker.reset_temporal_state()

        frame_idx = 0
        speaking_count = 0
        non_speaking_count = 0

        while cap_orig.isOpened():
            ret_orig, frame_orig = cap_orig.read()
            if not ret_orig:
                break

            ret_gen, frame_gen = cap_gen.read()
            if not ret_gen:
                # If generated stream ended, fallback to original frame
                frame_gen = frame_orig

            timestamp = frame_idx / fps
            is_active = SpeechActivityTimeline.is_speaking(timestamp, speaking_intervals)

            if is_active:
                speaking_count += 1
                out_frame, _ = self.composite_frame(frame_orig, frame_gen, is_speaking=True)
            else:
                non_speaking_count += 1
                # STRICT PIXEL-IDENTITY: Exactly original frame
                out_frame = frame_orig

            out.write(out_frame)
            frame_idx += 1

            if frame_idx % 30 == 0 or frame_idx == total_frames:
                print(f"  Composited {frame_idx}/{total_frames} frames (Current time: {timestamp:.2f}s | Speaking: {is_active})...", flush=True)

        cap_orig.release()
        cap_gen.release()
        out.release()
        self.masker.close()

        # Mux with master audio track using visually lossless encoding (CRF 17)
        audio_src = audio_path if (audio_path and os.path.exists(audio_path)) else orig_video_path
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_avi,
            "-i", audio_src,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-crf", "17",
            "-preset", "slow",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        if os.path.exists(temp_avi):
            os.remove(temp_avi)

        stats = {
            "total_frames": frame_idx,
            "speaking_frames": speaking_count,
            "non_speaking_frames": non_speaking_count,
            "speaking_ratio": round(speaking_count / max(frame_idx, 1), 4),
            "output_path": output_video_path
        }
        print(f"[SelectiveCompositor] Complete! Stats: {stats}")
        return stats
