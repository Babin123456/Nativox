"""
target_analyzer.py — Analyzes the generated Hindi/Bengali TTS audio.

Runs the same feature extraction pipeline on the target audio that was
run on the source English audio.  Outputs are saved to:
    outputs/spm/<video_stem>_<lang>_target_analysis.json

This enables source-vs-target comparison and prosody matching.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

from .vocal_performance import VocalPerformanceAnalyzer
from .emotion_analyzer import EmotionAnalyzer
from .performance_memory import _json_default


class TargetAudioAnalyzer:
    """
    Analyzes the generated target-language audio (Hindi or Bengali TTS output).

    Parameters
    ----------
    output_dir : directory to save the analysis JSON.
    sr         : sample rate.
    """

    def __init__(self, output_dir: str, sr: int = 16_000):
        self.output_dir = output_dir
        self.sr = sr
        os.makedirs(output_dir, exist_ok=True)

    def analyze(
        self,
        audio_path: str,
        video_stem: str,
        target_lang: str,
        gender: str = "male",
        speech_chunks=None,
    ) -> dict:
        """
        Full analysis of TTS output audio.

        Parameters
        ----------
        audio_path   : path to generated WAV file (16-kHz mono).
        video_stem   : used for output file naming.
        target_lang  : "hi" or "bn".
        gender       : speaker gender (affects semitone anchor).
        speech_chunks: list of chunk dicts for chunk-level emotion analysis.

        Returns
        -------
        Analysis dict (also saved to disk).
        """
        print(f"[TargetAnalyzer] Analyzing target audio: {audio_path}")

        vp_analyzer = VocalPerformanceAnalyzer(sr=self.sr)
        em_analyzer = EmotionAnalyzer(use_model=False)  # heuristic by default

        # Vocal performance (no Whisper segments for TTS — timestamps not needed)
        try:
            vp = vp_analyzer.analyze(audio_path, whisper_segments=None, speaker_gender=gender)
            vp_dict = vp.to_dict()
        except Exception as e:
            print(f"[TargetAnalyzer] Vocal performance error: {e}")
            vp_dict = {}

        # Emotion analysis
        try:
            if speech_chunks:
                chunk_dicts = [c.to_dict() if hasattr(c, "to_dict") else c for c in speech_chunks]
                emotion_segs = em_analyzer.analyze_chunks(audio_path, chunk_dicts)
            else:
                # Use full-audio windows
                from .performance_memory import PerformanceMemory
                from .schema import VocalPerformanceProfile
                duration_s = vp.f0_times_s[-1] if vp.f0_times_s else 10.0
                emotion_segs = em_analyzer.analyze_full_audio(audio_path, duration_s)
            emotion_dicts = [e.to_dict() for e in emotion_segs]
        except Exception as e:
            print(f"[TargetAnalyzer] Emotion analysis error: {e}")
            emotion_dicts = []

        result = {
            "audio_path": audio_path,
            "video_stem": video_stem,
            "target_lang": target_lang,
            "gender": gender,
            "vocal_performance": vp_dict,
            "emotion_segments": emotion_dicts,
        }

        out_path = os.path.join(
            self.output_dir, f"{video_stem}_{target_lang}_target_analysis.json"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=_json_default)

        print(f"[TargetAnalyzer] Saved target analysis → {out_path}")
        return result
