from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()

@dataclass
class PipelineConfig:
    input_video: Path
    target_lang: str
    output_video: Path
    work_dir: Path = Path("work")
    dry_run: bool = False
    device: str = os.getenv("NATIVOX_DEVICE", "cpu")
    tts_provider: str = os.getenv("NATIVOX_TTS", "omnivoice")
