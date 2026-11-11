from .sarvam_adapter import SarvamAdapter
from .edgetts_adapter import EdgeTTSAdapter

def build_tts(cfg):
    options = {
        "free": EdgeTTSAdapter,
        "edgetts": EdgeTTSAdapter,
        "sarvam": SarvamAdapter
    }
    if cfg.tts_provider not in options:
        raise ValueError(f"Unknown TTS provider: {cfg.tts_provider}")
    return options[cfg.tts_provider](device=cfg.device)
