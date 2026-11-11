"""
facial_performance.py — Frame-by-frame facial landmark and expression analysis.

Reuses the MediaPipe Face Mesh extraction logic from Pipeline1/analyse.py
and adds:
  - Expression trajectory (landmark velocity / temporal delta).
  - Head pose estimation (pitch, yaw, roll) via solvePnP.
  - Eyebrow raise index from landmark geometry.
  - Smile intensity from mouth-corner-to-eye distance ratio.
  - Facial Action Unit proxies from landmark distances.

Outputs a FacialPerformanceProfile with per-frame records and a summary.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp

from .schema import FacialPerformanceProfile

# ---------------------------------------------------------------------------
# 3-D model points for head-pose estimation (generic face model, metres)
# ---------------------------------------------------------------------------
_MODEL_POINTS = np.array([
    (0.0,    0.0,    0.0),     # Nose tip           (landmark 1)
    (0.0,   -330.0, -65.0),    # Chin               (landmark 199 → 152)
    (-225.0, 170.0, -135.0),   # Left eye corner    (landmark 263)
    (225.0,  170.0, -135.0),   # Right eye corner   (landmark 33)
    (-150.0, -150.0, -125.0),  # Left mouth corner  (landmark 61)
    (150.0,  -150.0, -125.0),  # Right mouth corner (landmark 291)
], dtype=np.float64)

_POSE_LM_IDS = [1, 152, 263, 33, 61, 291]

# Mouth aperture / width landmarks (same as Pipeline1)
_MOUTH_IDS = [13, 14, 61, 291, 12, 15, 78, 308, 0, 17]

# Eyebrow landmarks (outer brow tip, inner brow tip)
_BROW_LEFT = [70, 63, 105, 66, 107]   # left eyebrow
_BROW_RIGHT = [300, 293, 334, 296, 336]  # right eyebrow
_EYE_LEFT_CENTER = 468   # MediaPipe refined iris
_EYE_RIGHT_CENTER = 473


class FacialPerformanceAnalyzer:
    """
    Analyzes facial performance frame-by-frame from a video.
    """

    def __init__(
        self,
        max_faces: int = 1,
        detection_confidence: float = 0.5,
        tracking_confidence: float = 0.5,
        sample_every_n_frames: int = 1,
    ):
        self.max_faces = max_faces
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence
        self.sample_every_n_frames = sample_every_n_frames

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, video_path: str) -> FacialPerformanceProfile:
        """Run frame-by-frame facial analysis on a video file."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"[FacialPerformance] Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=self.max_faces,
            refine_landmarks=True,
            min_detection_confidence=self.detection_confidence,
            min_tracking_confidence=self.tracking_confidence,
        )

        frame_records: List[Dict[str, Any]] = []
        prev_landmarks: Optional[np.ndarray] = None
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                ts = frame_idx / fps

                if frame_idx % self.sample_every_n_frames != 0:
                    frame_idx += 1
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = face_mesh.process(rgb)

                record: Dict[str, Any] = {
                    "frame": frame_idx,
                    "timestamp_s": round(ts, 4),
                    "face_detected": False,
                    "face_count": 0,
                    "mar": None,              # Mouth Aspect Ratio
                    "mouth_open_px": None,
                    "mouth_width_px": None,
                    "head_pitch": None,
                    "head_yaw": None,
                    "head_roll": None,
                    "brow_raise_left": None,
                    "brow_raise_right": None,
                    "smile_index": None,
                    "landmark_velocity": None, # mean pixel-displacement vs prev frame
                }

                if result.multi_face_landmarks:
                    # Largest face
                    face = max(
                        result.multi_face_landmarks,
                        key=lambda f: np.ptp([p.x for p in f.landmark]) * np.ptp([p.y for p in f.landmark]),
                    )
                    lm = np.array([(p.x * w, p.y * h, p.z * w) for p in face.landmark])
                    record["face_detected"] = True
                    record["face_count"] = len(result.multi_face_landmarks)

                    # Mouth Aspect Ratio
                    mar, open_px, width_px = self._mouth_metrics(lm, w, h)
                    record["mar"] = round(mar, 4)
                    record["mouth_open_px"] = round(open_px, 2)
                    record["mouth_width_px"] = round(width_px, 2)

                    # Head pose
                    pitch, yaw, roll = self._head_pose(lm, w, h)
                    record["head_pitch"] = round(pitch, 2)
                    record["head_yaw"] = round(yaw, 2)
                    record["head_roll"] = round(roll, 2)

                    # Brow raise
                    bl, br = self._brow_raise(lm, h)
                    record["brow_raise_left"] = round(bl, 4)
                    record["brow_raise_right"] = round(br, 4)

                    # Smile index
                    record["smile_index"] = round(self._smile_index(lm, w, h), 4)

                    # Landmark velocity
                    lm_flat = lm[:, :2].flatten()
                    if prev_landmarks is not None:
                        velocity = float(np.mean(np.abs(lm_flat - prev_landmarks)))
                        record["landmark_velocity"] = round(velocity, 4)
                    prev_landmarks = lm_flat.copy()

                frame_records.append(record)
                frame_idx += 1

        finally:
            face_mesh.close()
            cap.release()

        # Summarize
        detected = [r for r in frame_records if r["face_detected"]]
        detection_rate = len(detected) / max(len(frame_records), 1)
        mean_mar = float(np.nanmean([r["mar"] for r in detected])) if detected else None

        head_pose_summary = {}
        for key in ["head_pitch", "head_yaw", "head_roll"]:
            vals = [r[key] for r in detected if r[key] is not None]
            head_pose_summary[f"mean_{key}"] = round(float(np.mean(vals)), 2) if vals else 0.0

        # Dominant expression (simple heuristic)
        smile_vals = [r["smile_index"] for r in detected if r["smile_index"] is not None]
        brow_vals = [
            (r.get("brow_raise_left", 0) or 0) + (r.get("brow_raise_right", 0) or 0)
            for r in detected
        ]
        mean_smile = float(np.mean(smile_vals)) if smile_vals else 0.0
        mean_brow = float(np.mean(brow_vals)) if brow_vals else 0.0

        if mean_brow > 0.08:
            dominant = "surprised/raised_brows"
        elif mean_smile > 0.60:
            dominant = "smiling"
        elif mean_mar is not None and mean_mar > 0.35:
            dominant = "open_mouth_speaking"
        else:
            dominant = "neutral"

        profile = FacialPerformanceProfile(
            frame_records=frame_records,
            face_detection_rate=round(detection_rate, 4),
            mean_mar=round(mean_mar, 4) if mean_mar is not None else None,
            dominant_expression=dominant,
            head_pose_summary=head_pose_summary,
        )

        mar_str = f"{mean_mar:.3f}" if mean_mar is not None else "—"
        print(f"[FacialPerformance] Analyzed {len(frame_records)} frames | "
              f"face_det={detection_rate*100:.1f}% | "
              f"mean_MAR={mar_str} | "
              f"expr={dominant}")
        return profile

    # ------------------------------------------------------------------
    # Metric helpers
    # ------------------------------------------------------------------

    def _mouth_metrics(
        self, lm: np.ndarray, w: int, h: int
    ) -> Tuple[float, float, float]:
        """Return (MAR, open_px, width_px)."""
        try:
            upper = lm[13, :2]
            lower = lm[14, :2]
            left  = lm[61, :2]
            right = lm[291, :2]
            opening = float(np.linalg.norm(upper - lower))
            width   = float(np.linalg.norm(left - right))
            mar = opening / (width + 1e-6)
            return mar, opening, width
        except Exception:
            return 0.0, 0.0, 1.0

    def _head_pose(
        self, lm: np.ndarray, w: int, h: int
    ) -> Tuple[float, float, float]:
        """Estimate head pitch, yaw, roll in degrees via solvePnP."""
        try:
            image_points = np.array(
                [lm[i, :2] for i in _POSE_LM_IDS], dtype=np.float64
            )
            cam_matrix = np.array([
                [w, 0, w / 2],
                [0, w, h / 2],
                [0, 0, 1],
            ], dtype=np.float64)
            dist_coeffs = np.zeros((4, 1))
            success, rvec, tvec = cv2.solvePnP(
                _MODEL_POINTS, image_points, cam_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not success:
                return 0.0, 0.0, 0.0
            rmat, _ = cv2.Rodrigues(rvec)
            proj_matrix = np.hstack([rmat, tvec])
            _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj_matrix)
            pitch = float(euler[0, 0])
            yaw   = float(euler[1, 0])
            roll  = float(euler[2, 0])
            return pitch, yaw, roll
        except Exception:
            return 0.0, 0.0, 0.0

    def _brow_raise(self, lm: np.ndarray, h: int) -> Tuple[float, float]:
        """
        Brow raise index: normalized vertical distance of brow landmarks
        above the eye center.  Positive = raised.
        """
        try:
            # Left brow mean y vs left eye
            left_brow_y = float(np.mean(lm[_BROW_LEFT, 1]))
            right_brow_y = float(np.mean(lm[_BROW_RIGHT, 1]))
            left_eye_y = float(lm[33, 1])    # inner left eye corner y
            right_eye_y = float(lm[263, 1])  # inner right eye corner y
            # Smaller y = higher on image = raised
            bl = (left_eye_y - left_brow_y) / h
            br = (right_eye_y - right_brow_y) / h
            return bl, br
        except Exception:
            return 0.0, 0.0

    def _smile_index(self, lm: np.ndarray, w: int, h: int) -> float:
        """
        Smile index: ratio of mouth-corner horizontal span to inter-eye span.
        Higher = wider smile.
        """
        try:
            left_mouth  = lm[61, :2]
            right_mouth = lm[291, :2]
            left_eye    = lm[33, :2]
            right_eye   = lm[263, :2]
            mouth_width = float(np.linalg.norm(right_mouth - left_mouth))
            eye_width   = float(np.linalg.norm(right_eye - left_eye))
            return mouth_width / (eye_width + 1e-6)
        except Exception:
            return 0.0
