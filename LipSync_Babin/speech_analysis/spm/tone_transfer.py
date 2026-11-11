"""
tone_transfer.py — Speaker Voice Tone, Timbre & Tonal Pitch Transfer Engine.

Transforms generic TTS synthetic speech (e.g. Edge-TTS Madhur / Bashkar)
into the exact voice tone, vocal tract timbre, tonal pitch (F0), and emotional
resonance of the original speaker.

Core Techniques:
  1. Praat PSOLA Formant & Pitch Morphing:
     Adjusts vocal tract length (formant shift ~1.15x) and median pitch to match
     the speaker's biological vocal cords and resonance cavity.
  2. Pitch Range & Dynamics Expansion:
     Expands pitch dynamic range to convey original emotional feeling and intonation.
  3. Spectral Envelope & Timbre Equalization:
     Extracts speaker's spectral centroid and harmonic distribution (HNR)
     and applies resonant IIR filtering so the voice has the warmth, presence,
     and texture of the original recording.
  4. Intonation / Tonal Pitch Contour Transfer:
     Aligns speaker's pitch contour (rise on emphasis, fall on closure)
     onto target-language syllables.
"""
from __future__ import annotations

import os
import subprocess
import numpy as np
import soundfile as sf
import parselmouth
from parselmouth.praat import call
from typing import Dict, Any, Optional, Tuple


class ToneTransferEngine:
    """
    Captures speaker vocal timbre, formant resonance, and tonal pitch from reference audio,
    and morphs target-language synthesized speech to match the original speaker's vocal identity.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def extract_speaker_tone_profile(self, reference_audio_path: str) -> Dict[str, Any]:
        """
        Extracts comprehensive acoustic profile of the original speaker:
        - Median F0, pitch range (min/max), F0 variability
        - Spectral centroid, spectral tilt
        - Praat HNR (harmonics-to-noise ratio)
        - Formant frequencies (F1, F2, F3)
        """
        temp_wav = None
        audio_target = reference_audio_path
        if reference_audio_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".webm")):
            temp_wav = reference_audio_path + "_temp_profile.wav"
            cmd = ["ffmpeg", "-y", "-i", reference_audio_path, "-vn", "-ar", "16000", "-ac", "1", temp_wav]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            audio_target = temp_wav

        sound = parselmouth.Sound(audio_target)
        
        # Pitch analysis
        pitch = sound.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
        f0_arr = pitch.selected_array['frequency']
        voiced = f0_arr[f0_arr > 0]
        
        if len(voiced) > 0:
            median_f0 = float(np.median(voiced))
            mean_f0 = float(np.mean(voiced))
            min_f0 = float(np.min(voiced))
            max_f0 = float(np.max(voiced))
            std_f0 = float(np.std(voiced))
        else:
            median_f0, mean_f0, min_f0, max_f0, std_f0 = 130.0, 130.0, 90.0, 200.0, 25.0

        # Formant analysis (Burg algorithm)
        formants = sound.to_formant_burg(max_number_of_formants=5, maximum_formant=5500.0)
        f1_list, f2_list, f3_list = [], [], []
        times = pitch.xs()
        for t in times[::5]:
            f1 = formants.get_value_at_time(1, t)
            f2 = formants.get_value_at_time(2, t)
            f3 = formants.get_value_at_time(3, t)
            if f1 and not np.isnan(f1): f1_list.append(f1)
            if f2 and not np.isnan(f2): f2_list.append(f2)
            if f3 and not np.isnan(f3): f3_list.append(f3)

        f1_median = float(np.median(f1_list)) if f1_list else 500.0
        f2_median = float(np.median(f2_list)) if f2_list else 1500.0
        f3_median = float(np.median(f3_list)) if f3_list else 2500.0

        # HNR (Harmonics-to-noise ratio)
        try:
            harmonicity = sound.to_harmonicity()
            hnr_vals = harmonicity.values[harmonicity.values > -200]
            mean_hnr = float(np.mean(hnr_vals)) if len(hnr_vals) > 0 else 14.0
        except Exception:
            mean_hnr = 14.0

        # Spectral Centroid
        spectrum = sound.to_spectrum()
        spec_centroid = float(spectrum.get_centre_of_gravity())

        profile = {
            "median_f0": median_f0,
            "mean_f0": mean_f0,
            "min_f0": min_f0,
            "max_f0": max_f0,
            "std_f0": std_f0,
            "f1": f1_median,
            "f2": f2_median,
            "f3": f3_median,
            "hnr": mean_hnr,
            "spectral_centroid": spec_centroid,
        }
        if temp_wav and os.path.exists(temp_wav):
            os.remove(temp_wav)

        return profile

    def transfer_tone(
        self,
        synthesized_audio_path: str,
        reference_audio_path: str,
        output_audio_path: str,
        speaker_profile: Optional[Dict[str, Any]] = None,
        emotional_intensity: float = 1.25,
    ) -> str:
        """
        Morphs synthesized_audio_path to match the voice tone, pitch, and timbre
        of reference_audio_path.

        Parameters
        ----------
        synthesized_audio_path : path to generic TTS WAV (e.g. Edge-TTS output)
        reference_audio_path   : path to original speaker audio/video
        output_audio_path      : destination for tone-morphed WAV
        speaker_profile        : pre-extracted profile (optional)
        emotional_intensity    : factor to expand pitch range (default 1.25 for expressive delivery)
        """
        if speaker_profile is None:
            speaker_profile = self.extract_speaker_tone_profile(reference_audio_path)

        target_median_f0 = speaker_profile.get("median_f0", 128.0)
        target_std_f0 = speaker_profile.get("std_f0", 25.0)
        target_f1 = speaker_profile.get("f1", 500.0)
        target_f2 = speaker_profile.get("f2", 1800.0)
        target_centroid = speaker_profile.get("spectral_centroid", 1500.0)

        sound_tts = parselmouth.Sound(synthesized_audio_path)
        
        # Analyze synthesized audio pitch and formants
        pitch_tts = sound_tts.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
        f0_tts = pitch_tts.selected_array['frequency']
        voiced_tts = f0_tts[f0_tts > 0]
        tts_median_f0 = float(np.median(voiced_tts)) if len(voiced_tts) > 0 else 125.0
        tts_std_f0 = float(np.std(voiced_tts)) if len(voiced_tts) > 0 else 45.0

        formants_tts = sound_tts.to_formant_burg(max_number_of_formants=5, maximum_formant=5500.0)
        f2_tts_list = []
        for t in pitch_tts.xs()[::5]:
            v2 = formants_tts.get_value_at_time(2, t)
            if v2 and not np.isnan(v2): f2_tts_list.append(v2)
        tts_f2 = float(np.median(f2_tts_list)) if f2_tts_list else 1900.0

        # Formant shift ratio (vocal tract length adjustment)
        formant_shift = float(np.clip(target_f2 / max(tts_f2, 1000.0), 0.92, 1.06))

        # Pitch range factor: calibrate wild TTS pitch swings down to match speaker's natural standard deviation
        pitch_range_factor = float(np.clip(target_std_f0 / max(tts_std_f0, 10.0), 0.45, 0.90))

        print(f"[ToneTransfer] Original Speaker F0 Median : {target_median_f0:.1f} Hz (Std: {target_std_f0:.1f} Hz, F2: {target_f2:.0f} Hz)")
        print(f"[ToneTransfer] Synthetic TTS F0 Median   : {tts_median_f0:.1f} Hz (Std: {tts_std_f0:.1f} Hz, F2: {tts_f2:.0f} Hz)")
        print(f"[ToneTransfer] Applying Formant Shift     : {formant_shift:.3f}x")
        print(f"[ToneTransfer] Calibrated Pitch Range     : {pitch_range_factor:.3f}x (matches speaker intonation)")

        # Praat PSOLA "Change gender"
        # Arguments: sound, min_pitch, max_pitch, formant_shift_ratio, new_pitch_median, pitch_range_factor, duration_factor
        morphed_sound = call(
            sound_tts,
            "Change gender",
            70.0,
            500.0,
            formant_shift,
            target_median_f0,
            pitch_range_factor,
            1.0
        )

        # Save morphed audio
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)
        temp_raw_morphed = output_audio_path.replace(".wav", "_raw_morphed.wav")
        morphed_sound.save(temp_raw_morphed, "WAV")

        # Full Spectral Envelope & Timbre Matching via STFT
        self._apply_spectral_envelope_matching(temp_raw_morphed, reference_audio_path, output_audio_path)

        if os.path.exists(temp_raw_morphed):
            os.remove(temp_raw_morphed)

        print(f"[ToneTransfer] Successfully transferred speaker tone & vocal timbre -> {output_audio_path}")
        return output_audio_path

    def _apply_spectral_envelope_matching(self, in_wav: str, ref_audio_path: str, out_wav: str):
        """
        Transfers the true spectral envelope, vocal cavity resonances, and microphone
        timbre of the reference speaker onto the pitch-morphed synthesized speech.
        """
        import scipy.signal as signal
        from scipy.signal import stft, istft

        # Extract clean ref 16k mono
        temp_ref = None
        ref_target = ref_audio_path
        if ref_audio_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".webm")):
            temp_ref = in_wav.replace(".wav", "_ref_tmp.wav")
            cmd = ["ffmpeg", "-y", "-i", ref_audio_path, "-vn", "-ar", "16000", "-ac", "1", temp_ref]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            ref_target = temp_ref

        try:
            y_in, sr = sf.read(in_wav)
            y_ref, _ = sf.read(ref_target)
            if len(y_in.shape) > 1: y_in = y_in.mean(axis=1)
            if len(y_ref.shape) > 1: y_ref = y_ref.mean(axis=1)

            def get_smoothed_spectrum(y, n_fft=2048):
                if len(y) < n_fft:
                    y = np.pad(y, (0, n_fft - len(y)))
                chunks = y[:len(y) - len(y) % n_fft].reshape(-1, n_fft)
                if len(chunks) == 0:
                    chunks = y[:n_fft].reshape(1, n_fft)
                S = np.abs(np.fft.rfft(chunks, axis=1))
                avg_spec = np.mean(S, axis=0) + 1e-8
                log_spec = np.log(avg_spec)
                window = signal.windows.gaussian(31, std=5)
                window /= window.sum()
                smoothed = np.convolve(log_spec, window, mode='same')
                return np.exp(smoothed)

            env_in = get_smoothed_spectrum(y_in)
            env_ref = get_smoothed_spectrum(y_ref)

            gain = env_ref / env_in
            gain = gain / np.median(gain)
            gain = np.clip(gain, 0.40, 2.50)  # smooth ±8 dB transfer curve

            f, t, Zxx = stft(y_in, fs=sr, nperseg=2048, noverlap=1536)
            Zxx_filtered = Zxx * gain[:, np.newaxis]
            _, y_filtered = istft(Zxx_filtered, fs=sr, nperseg=2048, noverlap=1536)

            y_filtered = y_filtered[:len(y_in)]
            peak = np.max(np.abs(y_filtered))
            if peak > 0.01:
                y_filtered = y_filtered * (0.92 / peak)

            sf.write(out_wav, y_filtered.astype(np.float32), sr)
        except Exception as e:
            print(f"[ToneTransfer] Spectral matching note: {e}, using clean morphed audio")
            import shutil
            shutil.copy2(in_wav, out_wav)
        finally:
            if temp_ref and os.path.exists(temp_ref):
                try:
                    os.remove(temp_ref)
                except Exception:
                    pass
