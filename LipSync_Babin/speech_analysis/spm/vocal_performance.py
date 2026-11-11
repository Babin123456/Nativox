"""
vocal_performance.py — Extracts the original speaker's dynamic vocal performance.

Extracted features
------------------
Pitch (F0)        : librosa.pyin  → contour, semitone-normalized, voiced ratio
Energy            : librosa.feature.rms → contour (linear + dB)
Spectral          : centroid, bandwidth, rolloff, MFCCs (13)
Voice quality     : parselmouth (Praat) → jitter, shimmer, HNR
Temporal / rhythm : Whisper word timestamps → speech rate, pause intervals

All features carry timestamps so they can be temporally aligned later.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import numpy as np
import librosa
from typing import Optional, List, Dict, Any

from .schema import VocalPerformanceProfile, SpeakerProfile

# Parselmouth is optional — missing at import time is handled gracefully.
try:
    import parselmouth
    from parselmouth.praat import call as praat_call
    _PRAAT_OK = True
except ImportError:
    _PRAAT_OK = False


class VocalPerformanceAnalyzer:
    """
    Runs complete vocal performance analysis on a media file.

    Parameters
    ----------
    sr : int
        Sample-rate for librosa loading (default 16 000 Hz).
    hop_length : int
        Hop length in samples for frame-level features.
    n_mfcc : int
        Number of MFCC coefficients to extract.
    """

    def __init__(self, sr: int = 16_000, hop_length: int = 160, n_mfcc: int = 13):
        self.sr = sr
        self.hop_length = hop_length
        self.n_mfcc = n_mfcc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        media_path: str,
        whisper_segments: Optional[List[Dict[str, Any]]] = None,
        speaker_gender: str = "male",
    ) -> VocalPerformanceProfile:
        """
        Full analysis of a video or audio file.

        Parameters
        ----------
        media_path      : path to source video/audio.
        whisper_segments: pre-computed Whisper segment list (saves reloading ASR).
        speaker_gender  : used to set the F0 reference anchor for semitone normalisation.
        """
        wav_path = self._extract_audio(media_path)
        try:
            y, sr = librosa.load(wav_path, sr=self.sr, mono=True)
        except Exception as e:
            raise RuntimeError(f"[VocalPerformance] Could not load audio from {media_path}: {e}")

        profile = VocalPerformanceProfile(
            # --- pitch ---
            f0_contour=[],
            f0_times_s=[],
            f0_semitone_contour=[],
            f0_median_hz=0.0,
            f0_mean_hz=0.0,
            f0_min_hz=0.0,
            f0_max_hz=0.0,
            voiced_ratio=0.0,
            # --- energy ---
            rms_contour=[],
            rms_times_s=[],
            rms_db_contour=[],
            rms_mean=0.0,
            rms_std=0.0,
            # --- spectral ---
            spectral_centroid=[],
            spectral_bandwidth=[],
            spectral_rolloff=[],
            mfcc_mean=[],
            # --- voice quality ---
            jitter_local=None,
            shimmer_local=None,
            hnr_db=None,
            # --- temporal ---
            speech_rate_wps=None,
            pause_intervals=[],
            word_intervals=[],
        )

        # 1. F0 / pitch
        self._extract_pitch(y, sr, speaker_gender, profile)

        # 2. Energy (RMS)
        self._extract_energy(y, sr, profile)

        # 3. Spectral features
        self._extract_spectral(y, sr, profile)

        # 4. Voice quality via Praat
        self._extract_voice_quality(wav_path, profile)

        # 5. Temporal / rhythm from Whisper segments
        if whisper_segments:
            self._extract_temporal(whisper_segments, profile)

        # Clean up temp wav
        if wav_path != media_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass

        return profile

    def build_speaker_profile(
        self,
        media_path: str,
        gender: str,
        gender_confidence: float,
        vocal_profile: VocalPerformanceProfile,
    ) -> SpeakerProfile:
        """Builds a stable speaker identity profile from an already-analyzed vocal profile."""
        return SpeakerProfile(
            gender=gender,
            gender_confidence=gender_confidence,
            median_f0_hz=vocal_profile.f0_median_hz,
            f0_range_hz=(vocal_profile.f0_min_hz, vocal_profile.f0_max_hz),
            spectral_centroid_hz=float(np.mean(vocal_profile.spectral_centroid)) if vocal_profile.spectral_centroid else 0.0,
            spectral_bandwidth_hz=float(np.mean(vocal_profile.spectral_bandwidth)) if vocal_profile.spectral_bandwidth else 0.0,
            spectral_rolloff_hz=float(np.mean(vocal_profile.spectral_rolloff)) if vocal_profile.spectral_rolloff else 0.0,
            hnr_db=vocal_profile.hnr_db or 0.0,
            voice_sample_path=media_path,
            reference_video_path=media_path,
            extraction_model="librosa-0.10+parselmouth-0.4",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_audio(self, media_path: str) -> str:
        """Return a 16-kHz mono WAV path.  If media_path is already a WAV, returns it as-is."""
        if media_path.lower().endswith(".wav"):
            return media_path

        tmp = tempfile.NamedTemporaryFile(suffix="_spm_vp.wav", delete=False)
        tmp.close()
        cmd = [
            "ffmpeg", "-y", "-i", media_path,
            "-vn", "-ar", "16000", "-ac", "1",
            tmp.name,
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"[VocalPerformance] ffmpeg failed: {result.stderr.decode(errors='replace')}")
        return tmp.name

    def _extract_pitch(self, y: np.ndarray, sr: int, gender: str, out: VocalPerformanceProfile):
        """F0 via probabilistic YIN (pyin)."""
        fmin = librosa.note_to_hz("C2")  # ~65 Hz
        fmax = librosa.note_to_hz("C7")  # ~2093 Hz

        try:
            f0, voiced_flag, _ = librosa.pyin(
                y,
                fmin=fmin,
                fmax=fmax,
                sr=sr,
                hop_length=self.hop_length,
            )
        except Exception as e:
            print(f"[VocalPerformance] pyin failed: {e} — using zeros")
            n = len(y) // self.hop_length + 1
            f0 = np.zeros(n)
            voiced_flag = np.zeros(n, dtype=bool)

        times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=self.hop_length)
        voiced_f0 = f0[voiced_flag]

        median_f0 = float(np.nanmedian(voiced_f0)) if len(voiced_f0) > 0 else 100.0
        # Anchor for semitone normalisation
        anchor = 125.0 if gender == "male" else 210.0
        semitone_norm = [
            float(12.0 * np.log2(max(v, 1.0) / anchor)) if (not np.isnan(v) and v > 0) else float("nan")
            for v in f0
        ]

        out.f0_contour = [float(v) if not np.isnan(v) else None for v in f0]
        out.f0_times_s = times.tolist()
        out.f0_semitone_contour = [v if not np.isnan(v) else None for v in semitone_norm]
        out.f0_median_hz = round(median_f0, 2)
        out.f0_mean_hz = round(float(np.nanmean(voiced_f0)), 2) if len(voiced_f0) > 0 else 0.0
        out.f0_min_hz = round(float(np.nanmin(voiced_f0)), 2) if len(voiced_f0) > 0 else 0.0
        out.f0_max_hz = round(float(np.nanmax(voiced_f0)), 2) if len(voiced_f0) > 0 else 0.0
        out.voiced_ratio = round(float(voiced_flag.mean()), 4) if len(voiced_flag) > 0 else 0.0

        print(f"[VocalPerformance] F0: median={out.f0_median_hz:.1f}Hz, "
              f"range=[{out.f0_min_hz:.1f}–{out.f0_max_hz:.1f}], "
              f"voiced={out.voiced_ratio*100:.1f}%")

    def _extract_energy(self, y: np.ndarray, sr: int, out: VocalPerformanceProfile):
        """Frame-level RMS energy."""
        rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=self.hop_length)
        rms_db = 20 * np.log10(np.clip(rms, 1e-9, None))

        out.rms_contour = rms.tolist()
        out.rms_times_s = times.tolist()
        out.rms_db_contour = rms_db.tolist()
        out.rms_mean = round(float(np.mean(rms)), 6)
        out.rms_std = round(float(np.std(rms)), 6)

        print(f"[VocalPerformance] Energy: mean_rms={out.rms_mean:.4f}, "
              f"mean_dB={float(np.mean(rms_db)):.1f}dB")

    def _extract_spectral(self, y: np.ndarray, sr: int, out: VocalPerformanceProfile):
        """Spectral centroid, bandwidth, rolloff, MFCCs."""
        sc = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=self.hop_length)[0]
        sb = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=self.hop_length)[0]
        sr_arr = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=self.hop_length)[0]
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self.n_mfcc, hop_length=self.hop_length)

        out.spectral_centroid = sc.tolist()
        out.spectral_bandwidth = sb.tolist()
        out.spectral_rolloff = sr_arr.tolist()
        out.mfcc_mean = np.mean(mfcc, axis=1).tolist()

        print(f"[VocalPerformance] Spectral centroid mean: {float(np.mean(sc)):.1f} Hz")

    def _extract_voice_quality(self, wav_path: str, out: VocalPerformanceProfile):
        """Jitter, shimmer, HNR via Praat/parselmouth."""
        if not _PRAAT_OK:
            print("[VocalPerformance] parselmouth not available — skipping Praat voice quality")
            return
        try:
            sound = parselmouth.Sound(wav_path)
            duration = sound.duration

            # Pitch object needed for some measures
            pitch_obj = sound.to_pitch()

            # PointProcess for jitter/shimmer
            point_process = praat_call(sound, "To PointProcess (periodic, cc)", 75, 500)

            # Jitter (local %) — expressed as fraction
            if duration > 0.1:
                jitter = praat_call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
                out.jitter_local = round(float(jitter), 6) if jitter and not np.isnan(jitter) else None
            # Shimmer (local dB)
            if duration > 0.1:
                shimmer = praat_call(
                    [sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
                )
                out.shimmer_local = round(float(shimmer), 6) if shimmer and not np.isnan(shimmer) else None

            # HNR (harmonics-to-noise ratio)
            harmonicity = praat_call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
            hnr = praat_call(harmonicity, "Get mean", 0, 0)
            out.hnr_db = round(float(hnr), 2) if hnr and not np.isnan(hnr) else None

            print(f"[VocalPerformance] Praat: jitter={out.jitter_local}, "
                  f"shimmer={out.shimmer_local}, HNR={out.hnr_db}dB")
        except Exception as e:
            print(f"[VocalPerformance] Praat analysis note: {e}")

    def _extract_temporal(self, segments: List[Dict[str, Any]], out: VocalPerformanceProfile):
        """Extract speech rate, pause intervals, word timestamps from Whisper output."""
        word_intervals = []
        pause_intervals = []
        total_words = 0
        total_speech_dur = 0.0

        # Collect word-level timestamps if available
        for seg in segments:
            words = seg.get("words", [])
            if words:
                for w in words:
                    wi = {
                        "word": w.get("word", "").strip(),
                        "start_s": float(w.get("start", 0.0)),
                        "end_s": float(w.get("end", 0.0)),
                        "prob": float(w.get("probability", 1.0)),
                    }
                    word_intervals.append(wi)
                    total_words += 1
                    total_speech_dur += wi["end_s"] - wi["start_s"]
            else:
                # Segment-level fallback
                text_words = seg.get("text", "").split()
                seg_dur = float(seg.get("end", 0)) - float(seg.get("start", 0))
                total_words += len(text_words)
                total_speech_dur += seg_dur

        # Pause detection from word boundaries
        if len(word_intervals) > 1:
            for i in range(len(word_intervals) - 1):
                gap = word_intervals[i + 1]["start_s"] - word_intervals[i]["end_s"]
                if gap > 0.15:  # > 150ms = meaningful pause
                    pause_intervals.append({
                        "start_s": word_intervals[i]["end_s"],
                        "end_s": word_intervals[i + 1]["start_s"],
                        "dur_s": round(gap, 4),
                    })
        elif segments:
            # Segment-level pauses
            segs_sorted = sorted(segments, key=lambda s: s.get("start", 0))
            for i in range(len(segs_sorted) - 1):
                gap = segs_sorted[i + 1].get("start", 0) - segs_sorted[i].get("end", 0)
                if gap > 0.2:
                    pause_intervals.append({
                        "start_s": segs_sorted[i]["end"],
                        "end_s": segs_sorted[i + 1]["start"],
                        "dur_s": round(gap, 4),
                    })

        # Overall speech rate
        if total_speech_dur > 0.5 and total_words > 0:
            out.speech_rate_wps = round(total_words / total_speech_dur, 2)

        out.word_intervals = word_intervals
        out.pause_intervals = pause_intervals

        print(f"[VocalPerformance] Temporal: words={total_words}, "
              f"rate={out.speech_rate_wps} wps, pauses={len(pause_intervals)}")
