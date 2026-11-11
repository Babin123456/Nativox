from abc import ABC, abstractmethod
from pathlib import Path

class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, reference_audio: Path, prosody: dict) -> Path:
        """Return generated speech audio path."""
