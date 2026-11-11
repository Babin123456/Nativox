"""
prosody_matcher.py — Iterative prosody refinement loop.

Compares source-vs-target divergence metrics and re-synthesizes
chunks with adjusted Edge-TTS SSML prosody controls if divergence
exceeds configurable thresholds.

Algorithm
---------
For each iteration (up to max_iterations):
  1. Load source SPM and current target analysis.
  2. For each chunk, compare energy/pitch with source chunk.
  3. If divergence > threshold, update SSML rate/pitch/volume params.
  4. Re-synthesize that chunk.
  5. Re-assemble audio and re-analyze.
  6. Exit if all divergences below threshold or max iterations reached.

SSML controls:
  - prosody rate  : "+10%" to "-10%"  (speech speed)
  - prosody pitch : "+5Hz" to "-5Hz"  (vocal pitch shift)
  - prosody volume: "+3dB" to "-3dB"  (loudness)
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
from typing import List, Dict, Any, Optional

import numpy as np

from .schema import SpeechChunk
from .performance_memory import _json_default
from .target_analyzer import TargetAudioAnalyzer


class ProsodyMatcher:
    """
    Iterative prosody refinement engine.

    Parameters
    ----------
    max_iterations     : maximum refinement cycles (default 3).
    energy_threshold   : DTW distance threshold for energy (< = acceptable).
    pitch_threshold    : DTW distance threshold for pitch.
    output_dir         : directory for intermediate outputs.
    sr                 : sample rate.
    """

    def __init__(
        self,
        max_iterations: int = 3,
        energy_threshold: float = 0.15,
        pitch_threshold: float = 0.20,
        output_dir: str = "Pipeline2/outputs/spm",
        sr: int = 16_000,
    ):
        self.max_iterations = max_iterations
        self.energy_threshold = energy_threshold
        self.pitch_threshold = pitch_threshold
        self.output_dir = output_dir
        self.sr = sr
        os.makedirs(output_dir, exist_ok=True)

    def refine(
        self,
        chunks: List[SpeechChunk],
        source_spm: Dict[str, Any],
        target_lang: str,
        voices: Dict[str, str],   # {"hi": {"male": "...", ...}, ...}
        video_stem: str,
    ) -> List[SpeechChunk]:
        """
        Runs the refinement loop and returns updated chunks with new TTS outputs.

        Parameters
        ----------
        chunks      : list of SpeechChunk (must have tts_output_path set).
        source_spm  : loaded SPM dict for source energy/pitch reference.
        target_lang : "hi" or "bn".
        voices      : VOICES dict from speech_translation.py.
        video_stem  : for output naming.
        """
        refinement_history = []

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[ProsodyMatcher] ═══ Refinement iteration {iteration}/{self.max_iterations} ═══")

            improved = 0
            for idx, chunk in enumerate(chunks):
                if chunk.tts_output_path is None:
                    continue

                # Compare this chunk's energy vs source chunk
                src_vp = source_spm.get("vocal_performance", {})
                src_rms_times = src_vp.get("rms_times_s", [])
                src_rms = src_vp.get("rms_contour", [])
                src_f0_times = src_vp.get("f0_times_s", [])
                src_f0 = src_vp.get("f0_contour", [])

                # Slice source features to this chunk's time window
                src_rms_chunk = self._slice_by_time(src_rms, src_rms_times, chunk.start_s, chunk.end_s)
                src_f0_chunk  = self._slice_by_time(src_f0, src_f0_times, chunk.start_s, chunk.end_s)

                # Analyze target chunk audio
                try:
                    tgt_rms, tgt_f0 = self._analyze_chunk_audio(chunk.tts_output_path)
                except Exception as e:
                    print(f"  Chunk {idx}: audio analysis failed ({e}) — skipping")
                    continue

                # Compute divergence
                energy_div = self._divergence(src_rms_chunk, tgt_rms)
                pitch_div  = self._divergence(
                    [v for v in src_f0_chunk if v and v > 0],
                    [v for v in tgt_f0 if v and v > 0],
                )

                needs_fix = (
                    energy_div > self.energy_threshold or
                    pitch_div  > self.pitch_threshold
                )

                if not needs_fix:
                    continue

                # Compute SSML adjustments
                new_rate, new_pitch, new_volume = self._compute_ssml_adjustments(
                    src_rms_chunk, tgt_rms, src_f0_chunk, tgt_f0, chunk
                )

                # Re-synthesize
                new_path = chunk.tts_output_path.replace(".wav", f"_r{iteration}.wav")
                ok = self._synthesize(
                    text=chunk.target_text,
                    target_lang=target_lang,
                    voices=voices,
                    gender="male",
                    rate=new_rate,
                    pitch=new_pitch,
                    volume=new_volume,
                    output_wav=new_path,
                )

                if ok:
                    chunk.ssml_rate   = new_rate
                    chunk.ssml_pitch  = new_pitch
                    chunk.ssml_volume = new_volume
                    chunk.tts_output_path = new_path
                    chunk.refined = True
                    improved += 1
                    print(f"  Chunk {idx}: re-synthesized "
                          f"(rate={new_rate}, pitch={new_pitch}, vol={new_volume}) "
                          f"energy_div={energy_div:.3f}, pitch_div={pitch_div:.3f}")

            refinement_history.append({
                "iteration": iteration,
                "chunks_improved": improved,
            })

            if improved == 0:
                print(f"[ProsodyMatcher] No further improvements needed. Stopping early.")
                break

        # Save history
        hist_path = os.path.join(
            self.output_dir, f"{video_stem}_{target_lang}_prosody_history.json"
        )
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(refinement_history, f, indent=2, default=_json_default)

        print(f"[ProsodyMatcher] Refinement history → {hist_path}")
        return chunks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _slice_by_time(
        self,
        values: list,
        times: list,
        start_s: float,
        end_s: float,
    ) -> list:
        """Return values whose timestamps fall within [start_s, end_s]."""
        if not values or not times:
            return []
        result = []
        for t, v in zip(times, values):
            if start_s <= t <= end_s:
                result.append(v)
        return result or values[: max(1, len(values) // 4)]

    def _analyze_chunk_audio(self, wav_path: str):
        """Return (rms_contour, f0_contour) for a chunk WAV."""
        import librosa
        y, sr = librosa.load(wav_path, sr=self.sr, mono=True)
        rms = librosa.feature.rms(y=y, hop_length=160)[0].tolist()
        f0, voiced, _ = librosa.pyin(y, fmin=50, fmax=600, sr=sr, hop_length=160)
        f0_list = [float(v) if (not np.isnan(v) and voiced[i]) else None
                   for i, v in enumerate(f0)]
        return rms, f0_list

    def _divergence(self, a: list, b: list) -> float:
        """Normalised mean absolute divergence between two sequences."""
        a_arr = np.array([v for v in a if v is not None and not np.isnan(v)], dtype=np.float32)
        b_arr = np.array([v for v in b if v is not None and not np.isnan(v)], dtype=np.float32)
        if len(a_arr) == 0 or len(b_arr) == 0:
            return 0.5
        # Resample to same length
        n = min(200, max(len(a_arr), len(b_arr)))
        a_r = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a_arr)), a_arr)
        b_r = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(b_arr)), b_arr)
        # Normalise
        for arr in (a_r, b_r):
            mn, mx = arr.min(), arr.max()
            if mx - mn > 1e-9:
                arr[:] = (arr - mn) / (mx - mn)
        return float(np.mean(np.abs(a_r - b_r)))

    def _compute_ssml_adjustments(
        self,
        src_rms: list,
        tgt_rms: list,
        src_f0: list,
        tgt_f0: list,
        chunk: SpeechChunk,
    ):
        """
        Determine new SSML rate / pitch / volume based on source-target gap.
        """
        # Energy → volume adjustment (dB)
        src_e = np.mean([v for v in src_rms if v is not None]) if src_rms else 0.01
        tgt_e = np.mean([v for v in tgt_rms if v is not None]) if tgt_rms else 0.01
        energy_ratio = src_e / (tgt_e + 1e-9)
        db_adjust = int(np.clip(20 * np.log10(energy_ratio), -6, 6))
        new_volume = f"{db_adjust:+d}dB"

        # Pitch → pitch adjustment (Hz)
        src_p = float(np.nanmean([v for v in src_f0 if v and v > 0])) if any(v for v in src_f0 if v) else 100.0
        tgt_p = float(np.nanmean([v for v in tgt_f0 if v and v > 0])) if any(v for v in tgt_f0 if v) else 100.0
        pitch_diff = int(np.clip(src_p - tgt_p, -10, 10))
        new_pitch = f"{pitch_diff:+d}Hz"

        # Rate: keep existing unless chunk.refined is False
        # Slight slow-down if pitch divergence is high (may indicate rushing)
        rate_adj = 0
        if abs(pitch_diff) > 5:
            rate_adj = -5
        new_rate = f"{rate_adj:+d}%"

        return new_rate, new_pitch, new_volume

    def _synthesize(
        self,
        text: str,
        target_lang: str,
        voices: dict,
        gender: str,
        rate: str,
        pitch: str,
        volume: str,
        output_wav: str,
    ) -> bool:
        """Re-synthesize one chunk with new SSML prosody settings."""
        try:
            import edge_tts

            voice = voices.get(target_lang, {}).get(gender, "hi-IN-MadhurNeural")
            # Map volume "+3dB" → volume level not directly supported by edge_tts
            # Use rate and pitch; volume is hard to map directly
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            temp_mp3 = output_wav.replace(".wav", "_tmp.mp3")
            asyncio.run(communicate.save(temp_mp3))

            cmd = [
                "ffmpeg", "-y", "-i", temp_mp3,
                "-ar", "16000", "-ac", "1", output_wav,
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            if os.path.exists(temp_mp3):
                os.remove(temp_mp3)
            return True
        except Exception as e:
            print(f"  [ProsodyMatcher] Re-synthesis failed: {e}")
            return False
