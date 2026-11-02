import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.compare import TARGET_FPS


def make_plot(results, series, out_path):
    names = list(series.keys())
    rows = len(names) + 1
    fig, axes = plt.subplots(rows, 1, figsize=(11, 3.2 * rows))
    axes = np.atleast_1d(axes)

    for ax, name in zip(axes, names):
        reference, candidate = series[name]
        time = np.arange(len(reference)) / TARGET_FPS
        ax.plot(time, reference, label="Real Hindi (reference)", linewidth=1.6)
        ax.plot(time, candidate, label=name, linewidth=1.6)
        ax.set_title(f"{name}  |  correlation = {results[name]['correlation']:.2f}")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylabel("Mouth opening")
        ax.legend(loc="upper right")
        ax.grid(alpha=0.3)

    axis = axes[-1]
    scores = [results[name]["correlation"] for name in names]
    axis.bar(names, scores, color=["#e07a5f", "#3d9970"][:len(names)])
    axis.set_ylim(min(0, min(scores) - 0.05), 1)
    axis.set_title("Similarity to real Hindi (higher is better)")
    for index, score in enumerate(scores):
        axis.text(index, score, f"{score:.2f}", ha="center", va="bottom")

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
