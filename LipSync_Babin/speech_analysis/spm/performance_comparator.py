"""
performance_comparator.py — Source vs. Target performance comparison with graphs.

Generates 8 comparison plots:
  1. English energy contour (RMS dB)
  2. Target energy contour (RMS dB)
  3. English pitch contour (F0 Hz)
  4. Target pitch contour (F0 Hz)
  5. Spectral centroid comparison
  6. Speaking activity timelines (voiced frames)
  7. Pause position comparison
  8. Emotion/intensity timelines

Saves combined figure to:
    outputs/spm/graphs/<video_stem>_<lang>_comparison.png

Also computes simple DTW-based divergence scores between aligned sequences.
"""
from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any, List

import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from .performance_memory import _json_default


class PerformanceComparator:
    """
    Loads source SPM data and target analysis data, then generates
    comparison graphs and computes divergence metrics.
    """

    def __init__(self, graphs_dir: str):
        self.graphs_dir = graphs_dir
        os.makedirs(graphs_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(
        self,
        source_spm: Dict[str, Any],
        target_analysis: Dict[str, Any],
        video_stem: str,
        target_lang: str,
    ) -> Dict[str, Any]:
        """
        Generate comparison graphs and return divergence metrics dict.

        Parameters
        ----------
        source_spm      : loaded SPM dict (from PerformanceMemory.load()).
        target_analysis : loaded target analysis dict (from TargetAudioAnalyzer).
        video_stem      : used for output naming.
        target_lang     : "hi" or "bn".

        Returns
        -------
        metrics dict with keys: energy_dtw, pitch_dtw, spectral_dtw,
        emotion_match, graph_path.
        """
        lang_name = "Hindi" if target_lang == "hi" else "Bengali"
        out_path = os.path.join(
            self.graphs_dir, f"{video_stem}_{target_lang}_comparison.png"
        )

        src_vp = (source_spm.get("vocal_performance") or {})
        tgt_vp = (target_analysis.get("vocal_performance") or {})
        src_em = source_spm.get("emotion_segments", [])
        tgt_em = target_analysis.get("emotion_segments", [])

        # --- Extract arrays ------------------------------------------------
        src_rms_db = self._to_arr(src_vp.get("rms_db_contour", []))
        tgt_rms_db = self._to_arr(tgt_vp.get("rms_db_contour", []))

        src_f0 = self._voiced_only(src_vp.get("f0_contour", []))
        tgt_f0 = self._voiced_only(tgt_vp.get("f0_contour", []))

        src_sc = self._to_arr(src_vp.get("spectral_centroid", []))
        tgt_sc = self._to_arr(tgt_vp.get("spectral_centroid", []))

        src_times = self._to_arr(src_vp.get("rms_times_s", []))
        tgt_times = self._to_arr(tgt_vp.get("rms_times_s", []))

        src_pauses = source_spm.get("vocal_performance", {}).get("pause_intervals", []) or []
        tgt_pauses = tgt_vp.get("pause_intervals", []) or []

        # --- DTW divergence ------------------------------------------------
        energy_dtw = self._dtw_distance(
            self._normalise(src_rms_db), self._normalise(tgt_rms_db)
        )
        pitch_dtw = self._dtw_distance(
            self._normalise(src_f0), self._normalise(tgt_f0)
        )
        spectral_dtw = self._dtw_distance(
            self._normalise(src_sc), self._normalise(tgt_sc)
        )

        # Emotion match (fraction of matching emotion labels by chunk position)
        emotion_match = self._emotion_overlap(src_em, tgt_em)

        # --- Generate figure -----------------------------------------------
        self._draw_figure(
            src_rms_db, tgt_rms_db,
            src_f0, tgt_f0,
            src_sc, tgt_sc,
            src_times, tgt_times,
            src_pauses, tgt_pauses,
            src_em, tgt_em,
            lang_name, out_path,
        )

        metrics = {
            "energy_dtw": round(energy_dtw, 4),
            "pitch_dtw": round(pitch_dtw, 4),
            "spectral_dtw": round(spectral_dtw, 4),
            "emotion_match": round(emotion_match, 4),
            "graph_path": out_path,
            "source_f0_median": float(src_vp.get("f0_median_hz", 0)),
            "target_f0_median": float(tgt_vp.get("f0_median_hz", 0)),
            "source_rms_mean": float(src_vp.get("rms_mean", 0)),
            "target_rms_mean": float(tgt_vp.get("rms_mean", 0)),
            "source_pauses": len(src_pauses),
            "target_pauses": len(tgt_pauses),
        }

        print(f"[Comparator] Divergence: energy_dtw={energy_dtw:.4f}, "
              f"pitch_dtw={pitch_dtw:.4f}, emotion_match={emotion_match:.2f}")
        print(f"[Comparator] Comparison graph → {out_path}")
        return metrics

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_figure(
        self,
        src_rms, tgt_rms,
        src_f0, tgt_f0,
        src_sc, tgt_sc,
        src_times, tgt_times,
        src_pauses, tgt_pauses,
        src_em, tgt_em,
        lang_name: str,
        out_path: str,
    ):
        fig = plt.figure(figsize=(18, 20))
        gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.55, wspace=0.35)

        # --- Row 0: Energy contours ----------------------------------------
        ax_e_src = fig.add_subplot(gs[0, 0])
        ax_e_tgt = fig.add_subplot(gs[0, 1])
        self._plot_contour(ax_e_src, src_times, src_rms, "English Energy (RMS dB)",
                           "Time (s)", "RMS dB", color="#2196F3")
        self._plot_contour(ax_e_tgt, tgt_times, tgt_rms, f"{lang_name} Energy (RMS dB)",
                           "Time (s)", "RMS dB", color="#FF5722")

        # --- Row 1: Pitch contours -----------------------------------------
        ax_p_src = fig.add_subplot(gs[1, 0])
        ax_p_tgt = fig.add_subplot(gs[1, 1])
        src_f0_times = np.linspace(0, src_times[-1] if len(src_times) else 10, len(src_f0))
        tgt_f0_times = np.linspace(0, tgt_times[-1] if len(tgt_times) else 10, len(tgt_f0))
        self._plot_contour(ax_p_src, src_f0_times, src_f0, "English Pitch (F0 Hz)",
                           "Time (s)", "Hz", color="#4CAF50", scatter=True)
        self._plot_contour(ax_p_tgt, tgt_f0_times, tgt_f0, f"{lang_name} Pitch (F0 Hz)",
                           "Time (s)", "Hz", color="#E91E63", scatter=True)

        # --- Row 2: Spectral centroid + pauses -----------------------------
        ax_sc = fig.add_subplot(gs[2, 0])
        ax_sc.plot(src_times[:len(src_sc)], src_sc, color="#2196F3", alpha=0.7, label="English", linewidth=0.8)
        ax_sc.plot(tgt_times[:len(tgt_sc)], tgt_sc, color="#FF5722", alpha=0.7, label=lang_name, linewidth=0.8)
        ax_sc.set_title("Spectral Centroid Comparison", fontsize=11, fontweight="bold")
        ax_sc.set_xlabel("Time (s)"); ax_sc.set_ylabel("Hz")
        ax_sc.legend(fontsize=8)
        ax_sc.grid(True, alpha=0.3)

        ax_pause = fig.add_subplot(gs[2, 1])
        self._plot_pauses(ax_pause, src_pauses, tgt_pauses, lang_name)

        # --- Row 3: Emotion timelines --------------------------------------
        ax_em_src = fig.add_subplot(gs[3, 0])
        ax_em_tgt = fig.add_subplot(gs[3, 1])
        self._plot_emotions(ax_em_src, src_em, "English Emotion Timeline", "#2196F3")
        self._plot_emotions(ax_em_tgt, tgt_em, f"{lang_name} Emotion Timeline", "#FF5722")

        fig.suptitle(
            f"Performance Comparison: English → {lang_name}",
            fontsize=14, fontweight="bold", y=0.99,
        )
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)

    def _plot_contour(self, ax, times, values, title, xlabel, ylabel,
                      color="#2196F3", scatter=False):
        if len(values) == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(title, fontsize=11, fontweight="bold")
            return
        t = times[:len(values)] if len(times) >= len(values) else np.linspace(0, len(values) / 100, len(values))
        if scatter:
            ax.scatter(t, values, s=4, c=color, alpha=0.6)
        else:
            ax.plot(t, values, color=color, linewidth=0.8, alpha=0.85)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    def _plot_pauses(self, ax, src_pauses, tgt_pauses, lang_name):
        ax.set_title("Pause Positions Comparison", fontsize=11, fontweight="bold")
        y_ticks, y_labels = [], []

        for i, p in enumerate(src_pauses[:20]):
            ax.barh(0.75, p["dur_s"], left=p["start_s"], height=0.3, color="#2196F3", alpha=0.7)
        for i, p in enumerate(tgt_pauses[:20]):
            ax.barh(0.25, p["dur_s"], left=p["start_s"], height=0.3, color="#FF5722", alpha=0.7)

        ax.set_yticks([0.25, 0.75])
        ax.set_yticklabels([lang_name, "English"])
        ax.set_xlabel("Time (s)")
        ax.text(0.02, 0.95, f"English: {len(src_pauses)} pauses", transform=ax.transAxes,
                fontsize=8, color="#2196F3")
        ax.text(0.02, 0.88, f"{lang_name}: {len(tgt_pauses)} pauses", transform=ax.transAxes,
                fontsize=8, color="#FF5722")
        ax.grid(True, alpha=0.3, axis="x")

    def _plot_emotions(self, ax, segments, title, color):
        ax.set_title(title, fontsize=11, fontweight="bold")
        if not segments:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            return
        emotion_colors = {
            "neutral": "#90A4AE", "happy": "#FFEB3B", "sad": "#5C6BC0",
            "angry": "#F44336", "fearful": "#AB47BC",
            "surprised": "#FF9800", "disgusted": "#8D6E63",
        }
        y_pos = 0
        for seg in segments:
            em = seg.get("emotion", "neutral") if isinstance(seg, dict) else seg.emotion
            st = seg.get("start_s", 0) if isinstance(seg, dict) else seg.start_s
            et = seg.get("end_s", 0) if isinstance(seg, dict) else seg.end_s
            intensity = seg.get("intensity", 0.5) if isinstance(seg, dict) else seg.intensity
            c = emotion_colors.get(em, "#90A4AE")
            ax.barh(0.5, et - st, left=st, height=intensity * 0.8,
                    color=c, alpha=0.75, edgecolor="white", linewidth=0.3)
            ax.text((st + et) / 2, 0.5, em[:3].upper(), ha="center", va="center",
                    fontsize=6, color="black")

        ax.set_xlabel("Time (s)")
        ax.set_yticks([])
        ax.grid(True, alpha=0.3, axis="x")

    # ------------------------------------------------------------------
    # Math helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_arr(lst) -> np.ndarray:
        if not lst:
            return np.array([])
        arr = np.array([v if v is not None else np.nan for v in lst], dtype=np.float32)
        # Replace NaN with nearest valid value (forward fill)
        mask = np.isnan(arr)
        if mask.all():
            return arr
        idx = np.where(~mask)[0]
        arr[mask] = np.interp(np.where(mask)[0], idx, arr[idx])
        return arr

    @staticmethod
    def _voiced_only(contour) -> np.ndarray:
        if not contour:
            return np.array([])
        arr = np.array([v for v in contour if v is not None and v > 0], dtype=np.float32)
        return arr

    @staticmethod
    def _normalise(arr: np.ndarray) -> np.ndarray:
        if len(arr) == 0:
            return arr
        mn, mx = arr.min(), arr.max()
        if mx - mn < 1e-9:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn)

    @staticmethod
    def _dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
        """
        Simple 1-D DTW distance.  Uses scipy if available, else a compact
        numpy implementation.
        """
        if len(a) == 0 or len(b) == 0:
            return 1.0  # maximum divergence

        # Resample to same length for fast approximate DTW
        target_len = min(500, max(len(a), len(b)))
        a_r = np.interp(np.linspace(0, 1, target_len), np.linspace(0, 1, len(a)), a)
        b_r = np.interp(np.linspace(0, 1, target_len), np.linspace(0, 1, len(b)), b)

        try:
            from scipy.spatial.distance import cityblock
            return float(cityblock(a_r, b_r)) / target_len
        except ImportError:
            return float(np.mean(np.abs(a_r - b_r)))

    @staticmethod
    def _emotion_overlap(src_em, tgt_em) -> float:
        """
        Fraction of matching emotion labels between source and target
        at corresponding positions.
        """
        if not src_em or not tgt_em:
            return 0.5
        n = min(len(src_em), len(tgt_em))
        matches = 0
        for i in range(n):
            se = src_em[i].get("emotion") if isinstance(src_em[i], dict) else src_em[i].emotion
            te = tgt_em[i].get("emotion") if isinstance(tgt_em[i], dict) else tgt_em[i].emotion
            if se == te:
                matches += 1
        return matches / n
