import numpy as np

def selective_composite(original_frame, generated_frame, mouth_mask, speaking):
    if not speaking:
        return original_frame.copy()
    if original_frame.shape != generated_frame.shape:
        raise ValueError("Frame dimensions must match.")
    mask = np.asarray(mouth_mask, dtype=np.float32)
    if mask.ndim == 2: mask = mask[..., None]
    if mask.max() > 1: mask /= 255.0
    out = original_frame.astype(np.float32)*(1-mask) + generated_frame.astype(np.float32)*mask
    return np.clip(out, 0, 255).astype(original_frame.dtype)
