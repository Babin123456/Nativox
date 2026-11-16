from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class PipelineConfig:
    input_video: Path
    target_lang: str
    output_video: Path
    work_dir: Path = Path("work")
    dry_run: bool = False
    device: str = "cpu"
    tts_provider: str = "free"
