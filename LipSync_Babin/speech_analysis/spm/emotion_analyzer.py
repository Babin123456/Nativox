"""
emotion_analyzer.py — Chunk-level speech emotion analysis.

Strategy
--------
1. Primary: RMS energy + pitch features mapped to basic emotion heuristics.
   This is CPU-compatible and runs locally without large model downloads.

2. Extended (optional): transformers pipeline with an audio emotion model
   (ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition).
   Falls back to heuristics if transformers is unavailable or model fetch fails.

The analyzer works on speech chunks (from VocalPerformanceAnalyzer word
timestamps) and returns per-chunk emotion labels with confidence scores.

Do NOT assign a single emotion to the entire video — each chunk is
analyzed independently.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from typing import List, Dict, Any, Optional

import numpy as np
import librosa

from .schema import EmotionSegment


# Emotion labels (superset compatible with common models)
EMOTION_LABELS = ["neutral", "happy", "sad", "angry", "fearful", "surprised", "disgusted"]

# Heuristic thresholds
_HIGH_ENERGY_DB = -9.0    # dB RMS threshold for shouting / loud angry speech
_LOW_ENERGY_DB = -36.0    # dB RMS threshold for whisper / sad speech
_HIGH_PITCH_HZ = 240.0    # above = high excitement / surprised
_LOW_PITCH_HZ = 85.0      # below = low pitch drone


class EmotionAnalyzer:
    """
    Analyzes emotion per speech chunk.

    Parameters
    ----------
    use_model : bool
        If True, attempt to load a transformers wav2vec2 emotion model.
        Falls back to heuristics if model unavailable.
    sr : int
        Sample rate for audio loading.
    """

    def __init__(self, use_model: bool = False, sr: int = 16_000):
        self.sr = sr
        self._model_pipeline = None
        self._model_ok = False

        if use_model:
            self._try_load_model()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_chunks(
        self,
        audio_path: str,
        chunks: List[Dict[str, Any]],  # list of {start_s, end_s, ...}
    ) -> List[EmotionSegment]:
        """
        Analyze emotion for each chunk.

        Parameters
        ----------
        audio_path : path to source WAV file (16-kHz mono).
        chunks     : list of dicts with at least "start_s" and "end_s".

        Returns
        -------
        List of EmotionSegment instances.
        """
        y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        results: List[EmotionSegment] = []

        for chunk in chunks:
            start_s = float(chunk.get("start_s", 0.0))
            end_s   = float(chunk.get("end_s", 0.0))

            if end_s <= start_s:
                continue

            start_samp = int(start_s * sr)
            end_samp   = int(end_s * sr)
            segment_audio = y[start_samp:end_samp]

            if len(segment_audio) < sr * 0.1:   # skip < 100ms segments
                continue

            if self._model_ok and self._model_pipeline is not None:
                emotion, intensity, probs = self._model_inference(segment_audio, sr)
                source = "wav2vec2-emotion"
                confidence = max(probs.values()) if probs else 0.5
            else:
                emotion, intensity, probs = self._heuristic_emotion(segment_audio, sr)
                source = "heuristic"
                confidence = 0.6  # heuristics are low-confidence

            results.append(EmotionSegment(
                start_s=start_s,
                end_s=end_s,
                emotion=emotion,
                intensity=round(intensity, 3),
                probabilities=probs,
                confidence=confidence,
                source=source,
            ))

        print(f"[EmotionAnalyzer] Analyzed {len(results)} chunks "
              f"(method={'model' if self._model_ok else 'heuristic'})")
        return results

    def analyze_full_audio(self, audio_path: str, duration_s: float) -> List[EmotionSegment]:
        """
        Analyze the full audio by splitting into equal-sized windows (2-second default).
        Used when no chunk boundaries are available.
        """
        window = 2.0
        chunks = []
        t = 0.0
        while t < duration_s:
            chunks.append({"start_s": t, "end_s": min(t + window, duration_s)})
            t += window
        return self.analyze_chunks(audio_path, chunks)

    # ------------------------------------------------------------------
    # Heuristic emotion classifier
    # ------------------------------------------------------------------

    def _heuristic_emotion(
        self, audio: np.ndarray, sr: int
    ) -> tuple:
        """
        Simple rule-based emotion classification from energy + pitch.
        Returns (emotion_str, intensity_float, probs_dict).
        """
        # Energy
        rms = float(np.sqrt(np.mean(audio ** 2)))
        rms_db = 20 * np.log10(max(rms, 1e-9))

        # Pitch (median voiced F0)
        try:
            f0, voiced, _ = librosa.pyin(
                audio, fmin=50, fmax=600, sr=sr,
                hop_length=160,
            )
            voiced_f0 = f0[voiced] if voiced is not None else np.array([])
            median_f0 = float(np.nanmedian(voiced_f0)) if len(voiced_f0) > 0 else 0.0
            voiced_ratio = float(voiced.mean()) if voiced is not None else 0.0
        except Exception:
            median_f0 = 0.0
            voiced_ratio = 0.5

        # Spectral variation (proxy for expressiveness)
        sc = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        sc_std = float(np.std(sc))

        # Rule-based decision
        probs = {e: 0.05 for e in EMOTION_LABELS}

        if rms_db > _HIGH_ENERGY_DB and median_f0 > _HIGH_PITCH_HZ:
            if sc_std > 400:
                emotion = "surprised"
                probs["surprised"] = 0.55; probs["happy"] = 0.25
            else:
                emotion = "happy"
                probs["happy"] = 0.55; probs["surprised"] = 0.20
        elif rms_db > _HIGH_ENERGY_DB and sc_std > 500:
            emotion = "angry"
            probs["angry"] = 0.55; probs["neutral"] = 0.20
        elif rms_db < _LOW_ENERGY_DB:
            emotion = "sad"
            probs["sad"] = 0.55; probs["neutral"] = 0.25
        elif rms_db > -20.0 and median_f0 > 170.0:
            emotion = "happy"
            probs["happy"] = 0.50; probs["neutral"] = 0.30
        elif voiced_ratio < 0.3:
            emotion = "neutral"
            probs["neutral"] = 0.65
        else:
            emotion = "neutral"
            probs["neutral"] = 0.60; probs["happy"] = 0.15

        # Normalize
        total = sum(probs.values())
        probs = {k: round(v / total, 4) for k, v in probs.items()}

        # Intensity: mapped from energy level
        intensity = np.clip((rms_db - (-45)) / 30.0, 0.0, 1.0)

        return emotion, float(intensity), probs

    # ------------------------------------------------------------------
    # Optional: transformers model inference
    # ------------------------------------------------------------------

    def _try_load_model(self):
        """Attempt to load a lightweight wav2vec2 emotion model."""
        try:
            from transformers import pipeline as hf_pipeline
            self._model_pipeline = hf_pipeline(
                "audio-classification",
                model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
                device=-1,  # CPU
            )
            self._model_ok = True
            print("[EmotionAnalyzer] Loaded wav2vec2 emotion model (CPU)")
        except Exception as e:
            print(f"[EmotionAnalyzer] Model not available ({e}) — using heuristic fallback")
            self._model_ok = False

    def _model_inference(self, audio: np.ndarray, sr: int) -> tuple:
        """Run transformer model on audio segment."""
        try:
            outputs = self._model_pipeline({"raw": audio, "sampling_rate": sr})
            probs = {item["label"].lower(): round(float(item["score"]), 4) for item in outputs}
            top = max(probs, key=probs.get)
            intensity = probs[top]
            # Normalize keys to our label set
            normalized = {}
            for k, v in probs.items():
                mapped = _map_emotion_label(k)
                normalized[mapped] = normalized.get(mapped, 0.0) + v
            return _map_emotion_label(top), intensity, normalized
        except Exception as e:
            print(f"[EmotionAnalyzer] Model inference error: {e} — using heuristic")
            return self._heuristic_emotion(audio, sr)


def _map_emotion_label(label: str) -> str:
    """Normalize various model label variants to our canonical set."""
    label = label.lower().strip()
    mapping = {
        "happiness": "happy", "joy": "happy",
        "sadness": "sad",
        "anger": "angry",
        "fear": "fearful",
        "disgust": "disgusted",
        "surprise": "surprised",
        "calm": "neutral",
    }
    return mapping.get(label, label if label in EMOTION_LABELS else "neutral")
