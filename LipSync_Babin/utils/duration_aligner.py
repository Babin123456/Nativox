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
    def detect_speech_boundaries(vocals_wav: Path, threshold_ratio: float = 0.08, window_s: float = 0.05) -> tuple[float, float]:
        """
        Detects active speech start and end timestamps (t_start, t_end) using acoustic RMS energy.
        Prevents silence cutting and false lip-sync on leading/trailing pauses.
        """
        try:
            data, sr = sf.read(str(vocals_wav))
            if data.ndim > 1:
                data = data.mean(axis=1)
            frame_len = int(sr * window_s)
            if frame_len <= 0 or len(data) < frame_len:
                return (0.0, len(data) / float(sr) if sr > 0 else 0.0)

            rms_list = []
            for i in range(0, len(data) - frame_len, frame_len):
                chunk = data[i:i + frame_len]
                rms_list.append(np.sqrt(np.mean(chunk**2)))

            max_rms = max(rms_list) if rms_list else 0.0
            if max_rms < 1e-4:
                return (0.0, len(data) / float(sr))

            thresh = max_rms * threshold_ratio
            active = [idx for idx, v in enumerate(rms_list) if v > thresh]
            if not active:
                return (0.0, len(data) / float(sr))

            # Add a small 100ms safety pad on boundaries
            t_start = max(0.0, (active[0] * window_s) - 0.10)
            t_end = min(len(data) / float(sr), ((active[-1] + 1) * window_s) + 0.10)
            return (t_start, t_end)
        except Exception:
            return (0.0, 0.0)

    @staticmethod
    def align_duration_to_video(
        speech_wav: Path,
        target_duration_s: float,
        output_wav: Path,
        sr: int = 16000,
        t_start_s: float = 0.0,
        t_end_s: float = None
    ) -> Path:
        """
        Aligns synthesized speech duration to the video timeline while locking speech
        strictly to the active speech window [t_start_s, t_end_s].
        Any leading silence (0.0 -> t_start) and trailing silence (t_end -> total)
        are padded with true silence so lips stay completely closed when the speaker is not speaking.
        """
        speech_wav = Path(speech_wav).resolve()
        output_wav = Path(output_wav).resolve()
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        data, file_sr = sf.read(speech_wav)
        if data.ndim > 1:
            data = data.mean(axis=1)

        cur_dur = len(data) / float(file_sr)
        target_total_dur = max(0.5, float(target_duration_s))
        
        # Calculate active speech window
        t_start = max(0.0, float(t_start_s))
        t_end = float(t_end_s) if t_end_s is not None and t_end_s > t_start else target_total_dur
        speech_window_dur = max(0.4, t_end - t_start)

        # Scale speech to fit the active speech window
        speed_ratio = cur_dur / speech_window_dur

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

        # Read scaled active speech
        scaled_speech, _ = sf.read(output_wav)
        active_target_samples = int(speech_window_dur * sr)
        if len(scaled_speech) < active_target_samples:
            scaled_speech = np.pad(scaled_speech, (0, active_target_samples - len(scaled_speech)))
        else:
            scaled_speech = scaled_speech[:active_target_samples]

        # Construct final audio with explicit leading and trailing silence
        lead_samples = int(t_start * sr)
        total_target_samples = int(target_total_dur * sr)
        trail_samples = max(0, total_target_samples - (lead_samples + len(scaled_speech)))

        lead_silence = np.zeros(lead_samples, dtype=np.float32)
        trail_silence = np.zeros(trail_samples, dtype=np.float32)

        final_track = np.concatenate([lead_silence, scaled_speech.astype(np.float32), trail_silence])
        if len(final_track) < total_target_samples:
            final_track = np.pad(final_track, (0, total_target_samples - len(final_track)))
        else:
            final_track = final_track[:total_target_samples]

        sf.write(output_wav, final_track.astype(np.float32), sr)
        return output_wav
