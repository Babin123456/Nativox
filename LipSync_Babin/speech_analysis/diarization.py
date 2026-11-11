from dataclasses import dataclass
from pathlib import Path

@dataclass
class SpeechInterval:
    start_time: float
    end_time: float
    speaker_id: str = "speaker_0"

def detect_speech_segments(audio_path: Path):
    raise NotImplementedError("Integrate Silero VAD/WebRTC VAD and speaker diarization.")
