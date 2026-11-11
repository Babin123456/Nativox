from dataclasses import asdict, dataclass, field
from pathlib import Path
import json

@dataclass
class SpeakerProfile:
    speaker_id: str
    voice_embedding: list[float] = field(default_factory=list)
    avg_f0: float = 0.0
    f0_range: float = 0.0
    avg_energy: float = 0.0
    dominant_language: str = "en"

@dataclass
class PerformanceSegment:
    start_time: float
    end_time: float
    emotion: str = "unknown"
    pitch_contour: list[float] = field(default_factory=list)
    energy_contour: list[float] = field(default_factory=list)
    speaking_rate: float = 0.0
    pauses: list[float] = field(default_factory=list)
    transcript_text: str = ""
    translated_text: str = ""

@dataclass
class PerformanceMemory:
    speakers: list[SpeakerProfile]
    segments: list[PerformanceSegment]
    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
    @classmethod
    def load(cls, path: Path):
        d = json.loads(path.read_text(encoding="utf-8"))
        return cls([SpeakerProfile(**x) for x in d["speakers"]],
                   [PerformanceSegment(**x) for x in d["segments"]])
