"""
Speaker Performance Memory (SPM) package.

Captures and stores the original speaker's vocal and facial
performance as structured, timestamped information.
"""
from .performance_memory import PerformanceMemory, load_spm
from .vocal_performance import VocalPerformanceAnalyzer
from .facial_performance import FacialPerformanceAnalyzer
from .emotion_analyzer import EmotionAnalyzer
from .target_analyzer import TargetAudioAnalyzer
from .performance_comparator import PerformanceComparator
from .prosody_matcher import ProsodyMatcher
from .quality_evaluator import QualityEvaluator

__all__ = [
    "PerformanceMemory",
    "load_spm",
    "VocalPerformanceAnalyzer",
    "FacialPerformanceAnalyzer",
    "EmotionAnalyzer",
    "TargetAudioAnalyzer",
    "PerformanceComparator",
    "ProsodyMatcher",
    "QualityEvaluator",
]
