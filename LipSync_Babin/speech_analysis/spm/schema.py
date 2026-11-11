"""
schema.py — Typed dataclasses for the Speaker Performance Memory (SPM) data contract.

Every feature record carries:
  - start_s / end_s : temporal interval in seconds
  - frame_idx       : optional frame index (video-derived features)
  - confidence      : extraction confidence in [0, 1]
  - source          : originating modality ("audio" | "video" | "asr")
  - model           : extraction tool/version string
  - values          : the actual feature dictionary
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Primitive building block
# ---------------------------------------------------------------------------
@dataclass
class FeatureRecord:
    start_s: float
    end_s: float
    values: Dict[str, Any]
    confidence: float = 1.0
    source: str = "audio"
    model: str = "unknown"
    frame_idx: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Stable speaker identity
# ---------------------------------------------------------------------------
@dataclass
class SpeakerProfile:
    gender: str                        # "male" | "female"
    gender_confidence: float
    median_f0_hz: float
    f0_range_hz: tuple                 # (min, max)
    spectral_centroid_hz: float
    spectral_bandwidth_hz: float
    spectral_rolloff_hz: float
    hnr_db: float                      # Harmonic-to-Noise Ratio
    voice_sample_path: str
    reference_video_path: str
    extraction_model: str = "librosa+parselmouth"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["f0_range_hz"] = list(d["f0_range_hz"])
        return d


# ---------------------------------------------------------------------------
# Dynamic vocal performance
# ---------------------------------------------------------------------------
@dataclass
class VocalPerformanceProfile:
    # Pitch
    f0_contour: List[float]            # frame-level F0 in Hz (nan = unvoiced)
    f0_times_s: List[float]            # timestamps corresponding to f0_contour
    f0_semitone_contour: List[float]   # semitone-normalized relative to median
    f0_median_hz: float
    f0_mean_hz: float
    f0_min_hz: float
    f0_max_hz: float
    voiced_ratio: float                # fraction of voiced frames

    # Energy
    rms_contour: List[float]           # frame-level RMS
    rms_times_s: List[float]
    rms_db_contour: List[float]        # dB version
    rms_mean: float
    rms_std: float

    # Spectral
    spectral_centroid: List[float]
    spectral_bandwidth: List[float]
    spectral_rolloff: List[float]
    mfcc_mean: List[float]             # 13 MFCCs, mean over utterance

    # Voice quality (Praat/parselmouth)
    jitter_local: Optional[float]
    shimmer_local: Optional[float]
    hnr_db: Optional[float]

    # Temporal / rhythm
    speech_rate_wps: Optional[float]   # words per second
    pause_intervals: List[Dict[str, float]]  # [{"start_s", "end_s", "dur_s"}]
    word_intervals: List[Dict[str, Any]]     # Whisper word-level timestamps

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Facial performance profile
# ---------------------------------------------------------------------------
@dataclass
class FacialPerformanceProfile:
    frame_records: List[Dict[str, Any]]   # one dict per frame
    face_detection_rate: float
    mean_mar: Optional[float]             # mean Mouth Aspect Ratio
    dominant_expression: Optional[str]
    head_pose_summary: Dict[str, float]   # mean pitch/yaw/roll

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Emotion segment
# ---------------------------------------------------------------------------
@dataclass
class EmotionSegment:
    start_s: float
    end_s: float
    emotion: str
    intensity: float
    probabilities: Dict[str, float]
    confidence: float
    source: str = "audio"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Speech chunk (phrase-level)
# ---------------------------------------------------------------------------
@dataclass
class SpeechChunk:
    chunk_id: int
    start_s: float
    end_s: float
    source_text: str
    target_text: str
    target_lang: str
    emotion: str
    emotion_intensity: float
    f0_median_hz: float
    rms_mean: float
    speech_rate_wps: Optional[float]
    pause_before_s: float
    pause_after_s: float
    ssml_rate: str    # e.g. "medium", "slow", "+5%"
    ssml_pitch: str   # e.g. "+0Hz"
    ssml_volume: str  # e.g. "+0dB"
    tts_output_path: Optional[str] = None
    refined: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Top-level SPM container
# ---------------------------------------------------------------------------
@dataclass
class SPMData:
    version: str = "1.0"
    video_path: str = ""
    video_stem: str = ""
    duration_s: float = 0.0

    # Stable identity
    speaker_profile: Optional[SpeakerProfile] = None

    # Dynamic performance
    vocal_performance: Optional[VocalPerformanceProfile] = None
    facial_performance: Optional[FacialPerformanceProfile] = None
    emotion_segments: List[EmotionSegment] = field(default_factory=list)
    speech_chunks: List[SpeechChunk] = field(default_factory=list)

    # Metadata
    english_transcript: str = ""
    whisper_segments: List[Dict[str, Any]] = field(default_factory=list)
    extraction_timestamp: str = ""
    extraction_models: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "version": self.version,
            "video_path": self.video_path,
            "video_stem": self.video_stem,
            "duration_s": self.duration_s,
            "speaker_profile": self.speaker_profile.to_dict() if self.speaker_profile else None,
            "vocal_performance": self.vocal_performance.to_dict() if self.vocal_performance else None,
            "facial_performance": self.facial_performance.to_dict() if self.facial_performance else None,
            "emotion_segments": [e.to_dict() for e in self.emotion_segments],
            "speech_chunks": [c.to_dict() for c in self.speech_chunks],
            "english_transcript": self.english_transcript,
            "whisper_segments": self.whisper_segments,
            "extraction_timestamp": self.extraction_timestamp,
            "extraction_models": self.extraction_models,
        }
        return d
