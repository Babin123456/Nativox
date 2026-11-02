import sys
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp

# Face landmark points used to measure the mouth
UPPER_LIP = 13
LOWER_LIP = 14
LEFT_CORNER = 61
RIGHT_CORNER = 291


def extract_curve(video_path):
    """Return (curve, fps). curve has one mouth-opening value per frame."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
    )

    values = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            values.append(np.nan)  # no face found in this frame
            continue

        lm = result.multi_face_landmarks[0].landmark
        up = np.array([lm[UPPER_LIP].x, lm[UPPER_LIP].y])
        low = np.array([lm[LOWER_LIP].x, lm[LOWER_LIP].y])
        left = np.array([lm[LEFT_CORNER].x, lm[LEFT_CORNER].y])
        right = np.array([lm[RIGHT_CORNER].x, lm[RIGHT_CORNER].y])

        opening = np.linalg.norm(up - low)
        width = np.linalg.norm(left - right)
        values.append(opening / width if width > 0 else np.nan)

    cap.release()
    face_mesh.close()

    curve = np.array(values, dtype=float)

    # Fill the frames where no face was found
    bad = np.isnan(curve)
    if bad.all():
        raise ValueError("No face detected in the whole video.")
    if bad.any():
        idx = np.arange(len(curve))
        curve[bad] = np.interp(idx[bad], idx[~bad], curve[~bad])

    return curve, fps


if __name__ == "__main__":
    video = Path(sys.argv[1])
    curve, fps = extract_curve(video)

    out_dir = Path(__file__).resolve().parents[2] / "output"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{video.stem}_curve.npy"
    np.save(out_file, curve)

    print(f"Frames: {len(curve)} | FPS: {fps:.1f}")
    print(f"Saved: {out_file}")
