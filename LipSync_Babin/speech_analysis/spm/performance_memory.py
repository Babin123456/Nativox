"""
performance_memory.py — Serialization, versioning, and I/O for SPM data.

Saves large arrays as .npy side-files so the main JSON stays readable.
"""
from __future__ import annotations

import json
import os
import datetime
import numpy as np
from typing import Optional
from .schema import SPMData


_SPM_VERSION = "1.0"


class PerformanceMemory:
    """
    Manages saving and loading of an SPMData object to/from disk.

    Layout::

        outputs/spm/<video_stem>_spm.json
        outputs/spm/<video_stem>_f0.npy       (F0 contour array)
        outputs/spm/<video_stem>_rms.npy      (RMS contour array)
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def save(self, spm: SPMData) -> str:
        """
        Persist an SPMData to disk.
        Returns the path of the saved JSON file.
        """
        spm.extraction_timestamp = datetime.datetime.now().isoformat()
        stem = spm.video_stem

        # Externalise large float arrays to .npy files
        npy_paths: dict = {}
        if spm.vocal_performance is not None:
            vp = spm.vocal_performance
            for attr, label in [
                ("f0_contour", "f0"),
                ("rms_contour", "rms"),
                ("spectral_centroid", "sc"),
            ]:
                arr = getattr(vp, attr, None)
                if arr is not None and len(arr) > 200:
                    npy_path = os.path.join(self.output_dir, f"{stem}_{label}.npy")
                    np.save(npy_path, np.array(arr, dtype=np.float32))
                    npy_paths[label] = npy_path
                    # Replace inline list with reference string
                    setattr(vp, attr, f"<npy:{npy_path}>")

        d = spm.to_dict()
        d["_npy_paths"] = npy_paths

        # Restore in-memory arrays after serialisation (do not mutate spm permanently)
        if spm.vocal_performance is not None:
            for attr, label in [
                ("f0_contour", "f0"),
                ("rms_contour", "rms"),
                ("spectral_centroid", "sc"),
            ]:
                if label in npy_paths:
                    setattr(spm.vocal_performance, attr, np.load(npy_paths[label]).tolist())

        json_path = os.path.join(self.output_dir, f"{stem}_spm.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False, default=_json_default)

        print(f"[SPM] Saved performance memory → {json_path}")
        return json_path

    def load(self, video_stem: str) -> Optional[dict]:
        """Load saved SPM dict for a given video stem."""
        json_path = os.path.join(self.output_dir, f"{video_stem}_spm.json")
        if not os.path.exists(json_path):
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            d = json.load(f)

        # Restore large arrays from .npy side-files
        npy_paths = d.pop("_npy_paths", {})
        vp = d.get("vocal_performance") or {}
        for attr, label in [("f0_contour", "f0"), ("rms_contour", "rms"), ("spectral_centroid", "sc")]:
            if label in npy_paths and os.path.exists(npy_paths[label]):
                vp[attr] = np.load(npy_paths[label]).tolist()

        return d


def load_spm(output_dir: str, video_stem: str) -> Optional[dict]:
    """Convenience function: load a saved SPM dict."""
    return PerformanceMemory(output_dir).load(video_stem)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _json_default(obj):
    if isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
