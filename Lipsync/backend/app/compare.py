import numpy as np
from scipy.signal import savgol_filter

from app.mouth_curve import extract_curve

TARGET_FPS = 25
MAX_LAG_SECONDS = 1.5


def to_common_timeline(curve, fps):
    """Resample so every video uses the same time steps."""
    times = np.arange(len(curve)) / fps
    new_times = np.arange(0, times[-1], 1 / TARGET_FPS)
    return np.interp(new_times, times, curve)


def clean(curve):
    """Smooth the curve and remove mouth-size differences between recordings."""
    if len(curve) < TARGET_FPS:
        raise ValueError("Video is too short. Use at least 1 second of talking.")
    smooth = savgol_filter(curve, window_length=7, polyorder=2)
    std = smooth.std()
    if std == 0:
        raise ValueError("Mouth did not move in this video.")
    return (smooth - smooth.mean()) / std


def pearson(a, b):
    if len(a) < 2 or a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def overlap(ref, other, lag):
    """lag > 0 means 'other' is delayed compared to 'ref'."""
    if lag >= 0:
        n = min(len(ref), len(other) - lag)
        return ref[:n], other[lag:lag + n]
    n = min(len(ref) + lag, len(other))
    return ref[-lag:-lag + n], other[:n]


def find_lag(ref, other):
    max_lag = int(MAX_LAG_SECONDS * TARGET_FPS)
    best_lag, best_score = 0, -np.inf
    for lag in range(-max_lag, max_lag + 1):
        a, b = overlap(ref, other, lag)
        if len(a) < TARGET_FPS:
            continue
        score = pearson(a, b)
        if score > best_score:
            best_lag, best_score = lag, score
    return best_lag


def dtw_path(a, b, band=50):
    """Stretch the two curves so they line up as well as possible."""
    n, m = len(a), len(b)
    band = max(band, abs(n - m) + 10)
    distance = np.full((n + 1, m + 1), np.inf)
    distance[0, 0] = 0
    for i in range(1, n + 1):
        low, high = max(1, i - band), min(m, i + band)
        for j in range(low, high + 1):
            cost = abs(a[i - 1] - b[j - 1])
            distance[i, j] = cost + min(
                distance[i - 1, j],
                distance[i, j - 1],
                distance[i - 1, j - 1],
            )

    i, j = n, m
    path = [(i - 1, j - 1)]
    while i > 1 or j > 1:
        options = [
            (distance[i - 1, j - 1], i - 1, j - 1),
            (distance[i - 1, j], i - 1, j),
            (distance[i, j - 1], i, j - 1),
        ]
        _, i, j = min(options)
        path.append((i - 1, j - 1))
    return path[::-1]


def compare_pair(ref, other):
    lag = find_lag(ref, other)
    aligned_ref, aligned_other = overlap(ref, other, lag)

    path = dtw_path(aligned_ref, aligned_other)
    warped_ref = np.array([aligned_ref[i] for i, _ in path])
    warped_other = np.array([aligned_other[j] for _, j in path])

    scores = {
        "correlation": round(pearson(aligned_ref, aligned_other), 3),
        "dtw_correlation": round(pearson(warped_ref, warped_other), 3),
        "error": round(float(np.mean(np.abs(aligned_ref - aligned_other))), 3),
        "delay_ms": int(lag * 1000 / TARGET_FPS),
    }
    return scores, aligned_ref, aligned_other


def run_comparison(real_path, candidates):
    """candidates = {"name": video_path}. Compare each with the reference."""
    ref_curve, ref_fps = extract_curve(real_path)
    reference = clean(to_common_timeline(ref_curve, ref_fps))

    results, series = {}, {}
    for name, path in candidates.items():
        curve, fps = extract_curve(path)
        other = clean(to_common_timeline(curve, fps))
        scores, aligned_ref, aligned_other = compare_pair(reference, other)
        results[name] = scores
        series[name] = (aligned_ref, aligned_other)
    return results, series
