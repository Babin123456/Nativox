import os
import subprocess
from pathlib import Path
import soundfile as sf
import numpy as np

class DurationAligner:
    """
    Ensures that the dubbed speech audio precisely matches the original video duration 
    and speech timing down to the millisecond so that Wav2Lip and the output video
    stay 100% in sync without cutting short or drifting.
    """
    @staticmethod
    def align_duration_to_video(speech_wav: Path, target_duration_s: float, output_wav: Path, sr: int = 16000) -> Path:
        speech_wav = Path(speech_wav).resolve()
        output_wav = Path(output_wav).resolve()
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        data, file_sr = sf.read(speech_wav)
        if data.ndim > 1:
            data = data.mean(axis=1)

        cur_dur = len(data) / float(file_sr)
        target_dur = max(0.5, float(target_duration_s))

        speed_ratio = cur_dur / target_dur

        # If length is slightly shorter or longer, adjust tempo with atempo filter
        if 0.5 <= speed_ratio <= 2.0:
            filter_str = f"atempo={speed_ratio:.4f}"
        else:
            filters = []
            rem = speed_ratio
            while rem > 2.0:
                filters.append("atempo=2.0")
                rem /= 2.0
            while rem < 0.5:
                filters.append("atempo=0.5")
                rem /= 0.5
            filters.append(f"atempo={rem:.4f}")
            filter_str = ",".join(filters)

        cmd = [
            "ffmpeg", "-y", "-i", str(speech_wav),
            "-filter:a", filter_str,
            "-ar", str(sr), "-ac", "1",
            str(output_wav)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Pad or trim to the exact target sample length
        scaled_data, _ = sf.read(output_wav)
        target_samples = int(target_dur * sr)
        if len(scaled_data) < target_samples:
            padding = np.zeros(target_samples - len(scaled_data), dtype=np.float32)
            scaled_data = np.concatenate([scaled_data, padding])
        elif len(scaled_data) > target_samples:
            scaled_data = scaled_data[:target_samples]

        sf.write(output_wav, scaled_data.astype(np.float32), sr)
        return output_wav
