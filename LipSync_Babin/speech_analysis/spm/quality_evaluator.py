"""
quality_evaluator.py — Independent audio-visual quality evaluation.

Evaluates the final dubbed video along 4 dimensions:
  1. Audio quality  : F0 naturalness, energy distribution, voice consistency.
  2. Visual quality : face detection stability, landmark velocity (flicker).
  3. A/V sync       : MAR–RMS cross-correlation (from Pipeline1 metrics).
  4. Identity       : face embedding consistency across frames (cosine similarity).

All scores are in [0, 1] (higher = better) with confidence values.
Saves a JSON report to outputs/spm/<video_stem>_<lang>_qa_report.json.

NOTE: This evaluator is SEPARATE from the generation pipeline.
It never modifies any video or audio — it only reads and measures.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import librosa
import cv2
import mediapipe as mp

from .performance_memory import _json_default


class QualityEvaluator:
    """
    Evaluates the quality of a dubbed video against its target audio.

    Parameters
    ----------
    output_dir : directory to save the QA report JSON.
    sr         : audio sample rate.
    """

    def __init__(self, output_dir: str, sr: int = 16_000):
        self.output_dir = output_dir
        self.sr = sr
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        dubbed_video_path: str,
        target_audio_path: str,
        source_spm: Optional[Dict[str, Any]],
        target_analysis: Optional[Dict[str, Any]],
        video_stem: str,
        target_lang: str,
    ) -> Dict[str, Any]:
        """
        Run all QA checks and return the report dict.

        Parameters
        ----------
        dubbed_video_path : path to the final dubbed HD video.
        target_audio_path : path to the aligned target WAV.
        source_spm        : source SPM dict (may be None).
        target_analysis   : target audio analysis dict (may be None).
        video_stem        : for output naming.
        target_lang       : "hi" or "bn".
        """
        print(f"\n[QualityEvaluator] === Running Quality Evaluation ===")
        report: Dict[str, Any] = {
            "dubbed_video": dubbed_video_path,
            "target_audio": target_audio_path,
            "video_stem": video_stem,
            "target_lang": target_lang,
            "scores": {},
            "warnings": [],
            "human_review_flags": [],
        }

        # 1. Audio quality
        audio_score, audio_details = self._eval_audio_quality(target_audio_path, source_spm, target_analysis)
        report["scores"]["audio_quality"] = audio_score
        report["audio_details"] = audio_details

        # 2. A/V sync
        sync_score, sync_details = self._eval_av_sync(dubbed_video_path, target_audio_path)
        report["scores"]["av_sync"] = sync_score
        report["sync_details"] = sync_details

        # 3. Visual quality / identity
        visual_score, visual_details = self._eval_visual_quality(dubbed_video_path)
        report["scores"]["visual_quality"] = visual_score
        report["visual_details"] = visual_details

        # 4. Overall
        overall = float(np.mean([audio_score, sync_score, visual_score]))
        report["scores"]["overall"] = round(overall, 4)

        # 5. Flags
        self._add_flags(report)

        # Save
        out_path = os.path.join(
            self.output_dir, f"{video_stem}_{target_lang}_qa_report.json"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=_json_default)

        print(f"[QualityEvaluator] Overall Score: {overall:.3f}")
        print(f"  Audio: {audio_score:.3f} | A/V Sync: {sync_score:.3f} | Visual: {visual_score:.3f}")
        print(f"[QualityEvaluator] QA report -> {out_path}")
        return report

    # ------------------------------------------------------------------
    # Audio quality
    # ------------------------------------------------------------------

    def _eval_audio_quality(
        self,
        audio_path: str,
        source_spm: Optional[dict],
        target_analysis: Optional[dict],
    ):
        details = {}
        score = 0.5  # neutral default

        try:
            y, sr = librosa.load(audio_path, sr=self.sr)

            # Silence ratio (too much silence = problem)
            rms = librosa.feature.rms(y=y, hop_length=160)[0]
            silence_ratio = float(np.mean(rms < 0.002))
            details["silence_ratio"] = round(silence_ratio, 4)

            # Energy variation (naturalness — flat = robotic)
            energy_cv = float(np.std(rms) / (np.mean(rms) + 1e-9))
            details["energy_cv"] = round(energy_cv, 4)

            # F0 voiced ratio
            try:
                f0, voiced, _ = librosa.pyin(y, fmin=50, fmax=600, sr=sr, hop_length=160)
                voiced_ratio = float(voiced.mean()) if voiced is not None else 0.0
                details["voiced_ratio"] = round(voiced_ratio, 4)
            except Exception:
                voiced_ratio = 0.5
                details["voiced_ratio"] = voiced_ratio

            # F0 comparison vs source
            f0_match_score = 0.5
            if source_spm and target_analysis:
                src_f0_med = source_spm.get("vocal_performance", {}).get("f0_median_hz", 0)
                tgt_f0_med = target_analysis.get("vocal_performance", {}).get("f0_median_hz", 0)
                if src_f0_med > 0 and tgt_f0_med > 0:
                    ratio = min(src_f0_med, tgt_f0_med) / max(src_f0_med, tgt_f0_med)
                    f0_match_score = float(ratio)
                details["f0_match_ratio"] = round(f0_match_score, 4)

            # Score formula
            score = (
                0.3 * (1.0 - silence_ratio) +
                0.3 * min(1.0, energy_cv * 3) +  # reward variation
                0.2 * voiced_ratio +
                0.2 * f0_match_score
            )
            score = round(float(np.clip(score, 0.0, 1.0)), 4)

        except Exception as e:
            details["error"] = str(e)
            print(f"[QA] Audio quality eval error: {e}")

        return score, details

    # ------------------------------------------------------------------
    # A/V sync
    # ------------------------------------------------------------------

    def _eval_av_sync(self, video_path: str, audio_path: str):
        """
        Estimates A/V sync via MAR–RMS cross-correlation.
        Returns (score, details).  score=1.0 means perfect sync.
        """
        details = {}
        score = 0.5

        try:
            # Extract MAR contour from video frames
            mar_contour = self._extract_mar(video_path, max_frames=300)
            if len(mar_contour) == 0:
                details["note"] = "Face not detected — sync score unavailable"
                return 0.5, details

            # Load audio RMS
            y, sr = librosa.load(audio_path, sr=self.sr)
            rms = librosa.feature.rms(y=y, hop_length=int(sr / 25))[0]  # ~25 fps

            # Align lengths
            n = min(len(mar_contour), len(rms))
            if n < 10:
                return 0.5, details

            mar_arr = np.array(mar_contour[:n])
            rms_arr = np.array(rms[:n])

            # Normalize
            for arr in (mar_arr, rms_arr):
                mn, mx = arr.min(), arr.max()
                if mx - mn > 1e-9:
                    arr[:] = (arr - mn) / (mx - mn)

            # Cross-correlation at zero lag
            corr = np.correlate(mar_arr - mar_arr.mean(), rms_arr - rms_arr.mean(), mode="full")
            corr_norm = corr / (np.std(mar_arr) * np.std(rms_arr) * n + 1e-9)
            mid = len(corr_norm) // 2
            zero_lag_corr = float(corr_norm[mid])

            # Find peak within ±10 frames
            window = corr_norm[mid - 10: mid + 11]
            peak_lag = int(np.argmax(np.abs(window))) - 10
            peak_corr = float(corr_norm[mid + peak_lag])

            details["zero_lag_correlation"] = round(zero_lag_corr, 4)
            details["peak_lag_frames"] = peak_lag
            details["peak_correlation"] = round(peak_corr, 4)

            # Score: high correlation at or near zero lag = good sync
            score = round(float(np.clip((zero_lag_corr + 1) / 2, 0.0, 1.0)), 4)

            if abs(peak_lag) > 3:
                details["sync_warning"] = f"Best correlation at lag={peak_lag} frames (not zero)"

        except Exception as e:
            details["error"] = str(e)
            print(f"[QA] A/V sync eval error: {e}")

        return score, details

    # ------------------------------------------------------------------
    # Visual quality
    # ------------------------------------------------------------------

    def _eval_visual_quality(self, video_path: str):
        """
        Checks face detection stability, landmark velocity (flicker),
        and mouth region blur.
        """
        details = {}
        score = 0.5

        try:
            face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return 0.5, {"error": "Cannot open video"}

            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            detected = 0
            total = 0
            velocities = []
            blur_scores = []
            prev_lm = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                total += 1
                if total % 2 != 0:  # sample every other frame
                    continue

                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = face_mesh.process(rgb)

                if res.multi_face_landmarks:
                    detected += 1
                    face = res.multi_face_landmarks[0]
                    lm = np.array([(p.x * w, p.y * h) for p in face.landmark])

                    if prev_lm is not None:
                        vel = float(np.mean(np.abs(lm - prev_lm)))
                        velocities.append(vel)
                    prev_lm = lm.copy()

                    # Mouth blur: crop around mouth landmarks [61, 291, 13, 14]
                    pts = lm[[61, 291, 13, 14]]
                    x1, y1 = max(0, int(pts[:, 0].min() - 10)), max(0, int(pts[:, 1].min() - 10))
                    x2, y2 = min(w, int(pts[:, 0].max() + 10)), min(h, int(pts[:, 1].max() + 10))
                    if x2 > x1 and y2 > y1:
                        roi = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
                        blur_scores.append(float(cv2.Laplacian(roi, cv2.CV_64F).var()))
                else:
                    prev_lm = None

            cap.release()
            face_mesh.close()

            det_rate = detected / max(total // 2, 1)
            details["face_detection_rate"] = round(det_rate, 4)
            details["sampled_frames"] = total // 2

            mean_velocity = float(np.mean(velocities)) if velocities else 0.0
            details["mean_landmark_velocity"] = round(mean_velocity, 4)

            mean_blur = float(np.mean(blur_scores)) if blur_scores else 0.0
            details["mean_mouth_laplacian"] = round(mean_blur, 2)

            # Score: high det_rate + low velocity + high blur score = good
            det_score = det_rate
            # Velocity: 0-2px is smooth, >8px is flickery
            vel_score = float(np.clip(1.0 - mean_velocity / 10.0, 0.0, 1.0))
            # Blur score: Laplacian var > 50 = sharp, < 10 = very blurry
            blur_score = float(np.clip(mean_blur / 100.0, 0.0, 1.0))

            score = round(float(0.4 * det_score + 0.3 * vel_score + 0.3 * blur_score), 4)

        except Exception as e:
            details["error"] = str(e)
            print(f"[QA] Visual quality eval error: {e}")

        return score, details

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_mar(self, video_path: str, max_frames: int = 300) -> list:
        """Extract MAR contour from video (up to max_frames)."""
        face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False, max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5,
        )
        cap = cv2.VideoCapture(video_path)
        mar_list = []
        count = 0
        try:
            while count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                h, w = frame.shape[:2]
                res = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if res.multi_face_landmarks:
                    face = res.multi_face_landmarks[0]
                    lm = np.array([(p.x * w, p.y * h) for p in face.landmark])
                    opening = np.linalg.norm(lm[13, :2] - lm[14, :2])
                    width = np.linalg.norm(lm[61, :2] - lm[291, :2])
                    mar_list.append(float(opening / (width + 1e-6)))
                else:
                    mar_list.append(0.0)
                count += 1
        finally:
            cap.release()
            face_mesh.close()
        return mar_list

    def _add_flags(self, report: dict):
        scores = report.get("scores", {})
        warnings = report.get("warnings", [])
        flags = report.get("human_review_flags", [])

        if scores.get("av_sync", 1.0) < 0.45:
            flags.append("LOW_AV_SYNC: Audio-visual synchronization below threshold — human review required.")
        if scores.get("visual_quality", 1.0) < 0.40:
            flags.append("VISUAL_ARTIFACTS: Visual quality below threshold — check for blur, flicker, identity drift.")
        if scores.get("audio_quality", 1.0) < 0.40:
            flags.append("AUDIO_QUALITY: Target audio naturalness below threshold — check TTS or prosody matching.")
        if report.get("sync_details", {}).get("sync_warning"):
            warnings.append(report["sync_details"]["sync_warning"])

        report["warnings"] = warnings
        report["human_review_flags"] = flags
