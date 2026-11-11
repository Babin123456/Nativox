from pathlib import Path
import numpy as np

def extract_pitch_energy(path: Path, start=0, end=None):
    import librosa
    y, sr = librosa.load(path, sr=16000, mono=True, offset=start,
                         duration=None if end is None else max(.01, end-start))
    f0, _, _ = librosa.pyin(y, fmin=50, fmax=500, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    return {"pitch_contour": [float(x) if np.isfinite(x) else 0.0 for x in f0],
            "energy_contour": [float(x) for x in rms],
            "avg_f0": float(np.nanmean(f0)) if np.isfinite(f0).any() else 0.0,
            "avg_energy": float(np.mean(rms)) if len(rms) else 0.0}

def extract_speaker_embedding(path: Path):
    raise NotImplementedError("Integrate SpeechBrain ECAPA-TDNN and its model checkpoint.")
