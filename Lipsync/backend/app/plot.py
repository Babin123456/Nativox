"""Render mouth-opening curves as a PNG."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_curves(
    curves: dict[str, np.ndarray],
    output_path: str | Path,
    fps: dict[str, float] | None = None,
) -> Path:
    """Save a comparison plot and return its path."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(12, 5))
    labels = {
        "real": ("Real Hindi", "#2563eb"),
        "dubbed": ("Dubbed", "#f59e0b"),
        "dubbed_lipsync": ("Dubbed + Lipsync", "#16a34a"),
    }
    for name, curve in curves.items():
        label, color = labels.get(name, (name.replace("_", " ").title(), None))
        rate = (fps or {}).get(name, 30.0)
        time = np.arange(curve.size) / rate
        axis.plot(time, curve, label=label, color=color, linewidth=1.2)
    axis.set_title("Mouth Opening Over Time")
    axis.set_xlabel("Time (seconds)")
    axis.set_ylabel("Normalized mouth opening")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output
