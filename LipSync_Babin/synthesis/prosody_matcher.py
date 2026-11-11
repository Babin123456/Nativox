import numpy as np

def compare_contours(source, generated):
    a, b = np.asarray(source, float), np.asarray(generated, float)
    if not len(a) or not len(b): return {"correlation": 0.0, "rmse": float("inf")}
    n = max(len(a), len(b))
    a = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a)), a)
    b = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(b)), b)
    corr = float(np.corrcoef(a, b)[0, 1]) if np.std(a) and np.std(b) else 0.0
    return {"correlation": corr, "rmse": float(np.sqrt(np.mean((a-b)**2)))}
