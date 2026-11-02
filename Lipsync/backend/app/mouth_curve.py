"""Extract a normalized mouth-opening curve from a video."""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

UPPER_LIP = 13
LOWER_LIP = 14
LEFT_MOUTH = 61
RIGHT_MOUTH = 291


def _interpolate_missing(values: list[float]) -> np.ndarray:
    curve = np.asarray(values, dtype=np.float32)
    valid = np.flatnonzero(np.isfinite(curve))
    if valid.size == 0:
        raise ValueError("No face was detected in the video.")
    if valid.size == 1:
        curve[:] = curve[valid[0]]
        return curve
    missing = np.flatnonzero(~np.isfinite(curve))
    if missing.size:
        curve[missing] = np.interp(missing, valid, curve[valid])
    return curve


def extract_mouth_curve(video_path: str | Path) -> tuple[np.ndarray, float]:
    """Return one mouth-opening value per frame and the video's FPS.

    The value is the distance between the upper and lower inner lip, divided
    by mouth width, making the curve less sensitive to camera distance.
    """
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    fps = fps if np.isfinite(fps) and fps > 0 else 30.0
    values: list[float] = []
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            result = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if not result.multi_face_landmarks:
                values.append(float("nan"))
                continue
            landmarks = result.multi_face_landmarks[0].landmark
            upper = landmarks[UPPER_LIP]
            lower = landmarks[LOWER_LIP]
            left = landmarks[LEFT_MOUTH]
            right = landmarks[RIGHT_MOUTH]
            opening = np.hypot(upper.x - lower.x, upper.y - lower.y)
            width = np.hypot(left.x - right.x, left.y - right.y)
            values.append(float(opening / width) if width > 1e-6 else float("nan"))
    finally:
        face_mesh.close()
        capture.release()

    if not values:
        raise ValueError(f"Video contains no readable frames: {video_path}")
    return _interpolate_missing(values), fps
