"""Align and compare mouth-opening curves."""

from __future__ import annotations

import numpy as np


def _resample(curve: np.ndarray, length: int) -> np.ndarray:
    if curve.size == length:
        return curve.astype(np.float32)
    positions = np.linspace(0, curve.size - 1, num=length)
    return np.interp(positions, np.arange(curve.size), curve).astype(np.float32)


def _standardize(curve: np.ndarray) -> np.ndarray:
    centered = curve - np.mean(curve)
    deviation = float(np.std(centered))
    return centered / deviation if deviation > 1e-8 else np.zeros_like(centered)


def compare_curves(
    reference: np.ndarray,
    candidate: np.ndarray,
    max_shift_ratio: float = 0.2,
    fps: float = 30.0,
) -> dict[str, float | int]:
    """Return the best Pearson-style correlation and frame alignment shift."""
    if reference.size < 2 or candidate.size < 2:
        raise ValueError("Each video must contain at least two readable frames.")

    length = max(reference.size, candidate.size)
    reference_aligned = _standardize(_resample(reference, length))
    candidate_aligned = _standardize(_resample(candidate, length))
    max_shift = max(1, int(length * max_shift_ratio))
    best_score = -1.0
    best_shift = 0

    for shift in range(-max_shift, max_shift + 1):
        if shift < 0:
            left = reference_aligned[-shift:]
            right = candidate_aligned[: length + shift]
        elif shift > 0:
            left = reference_aligned[: length - shift]
            right = candidate_aligned[shift:]
        else:
            left = reference_aligned
            right = candidate_aligned
        if left.size < 2:
            continue
        if np.std(left) <= 1e-8 or np.std(right) <= 1e-8:
            score = 0.0
        else:
            score = float(np.corrcoef(left, right)[0, 1])
        if score > best_score:
            best_score = score
            best_shift = shift

    return {
        "correlation": round(float(np.clip(best_score, -1.0, 1.0)), 4),
        "alignment_frames": best_shift,
        "alignment_seconds": round(best_shift / fps, 4),
    }


def compare_all(
    real_curve: np.ndarray,
    dubbed_curve: np.ndarray,
    lipsync_curve: np.ndarray,
    fps: float = 30.0,
) -> dict[str, dict[str, float | int]]:
    """Compare both dubbed versions against the real-video reference."""
    return {
        "dubbed": compare_curves(real_curve, dubbed_curve, fps=fps),
        "dubbed_lipsync": compare_curves(real_curve, lipsync_curve, fps=fps),
    }
