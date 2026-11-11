"""
dynamic_prosody_morpher.py — Dynamic F0 Pitch & Energy Emotional Prosody Transfer Engine.

Transfers the speaker's genuine emotional delivery, melodic intonation rises/falls,
emphasis peaks, and loudness dynamics from their original input video directly onto
synthesized target-language speech using Praat PSOLA pitch-tier resynthesis and
frame-level RMS energy envelope modulation.
"""
from __future__ import annotations

import os
import subprocess
import numpy as np
import soundfile as sf
import librosa
import parselmouth
from parselmouth.praat import call
from scipy.ndimage import gaussian_filter1d
from typing import Optional


class DynamicProsodyMorpher:
    """
    Transfers the dynamic emotional pitch contour (melody/intonation) and loudness/energy
    profile of an original speaker onto synthesized target-language speech.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def transfer_dynamic_prosody(
        self,
        synthesized_audio_path: str,
        reference_media_path: str,
        output_audio_path: str,
        pitch_expressiveness: float = 1.0,
        energy_expressiveness: float = 0.55,
    ) -> str:
        """
        Transfers dynamic emotional prosody from reference_media_path onto synthesized_audio_path.

        Parameters
        ----------
        synthesized_audio_path : Path to synthesized speech WAV
        reference_media_path   : Path to original English video or audio
        output_audio_path      : Destination path for the emotionally modulated speech
        pitch_expressiveness   : Scale factor for pitch variations (default 1.0)
        energy_expressiveness  : Exponent for loudness modulation (default 0.55)
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)

        temp_ref_wav = output_audio_path.replace(".wav", "_temp_ref_prosody.wav")
        cmd = [
            "ffmpeg", "-y",
            "-i", reference_media_path,
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            temp_ref_wav
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        try:
            # 1. Analyze synthesized speech
            snd_tts = parselmouth.Sound(synthesized_audio_path)
            pitch_tts = snd_tts.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
            f0_tts = pitch_tts.selected_array['frequency']
            t_tts = pitch_tts.xs()
            dur_tts = snd_tts.duration

            # 2. Analyze reference speaker pitch contour
            snd_ref = parselmouth.Sound(temp_ref_wav)
            pitch_ref = snd_ref.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
            f0_ref = pitch_ref.selected_array['frequency']
            t_ref = pitch_ref.xs()

            voiced_mask = f0_ref > 0
            if np.sum(voiced_mask) > 1:
                t_voiced = t_ref[voiced_mask]
                f0_voiced = f0_ref[voiced_mask]
                ref_median = float(np.median(f0_voiced))
                semitones_voiced = 12.0 * np.log2(f0_voiced / ref_median)

                t_voiced_norm = (t_voiced - t_ref[0]) / max(1e-5, (t_ref[-1] - t_ref[0]))
                t_tts_norm = (t_tts - t_tts[0]) / max(1e-5, (t_tts[-1] - t_tts[0]))

                # Interpolate continuously across voiced melody peaks (no unvoiced zero-flattening)
                mapped_semitones = np.interp(t_tts_norm, t_voiced_norm, semitones_voiced)
                # Light smoothing to preserve emotional pitch inflections, accents & questions
                mapped_semitones = gaussian_filter1d(mapped_semitones, sigma=1.5) * pitch_expressiveness
            else:
                ref_median = 130.0
                mapped_semitones = np.zeros_like(t_tts)

            # 3. Target dynamic pitch contour: anchor strictly to reference speaker's natural pitch
            tts_voiced = f0_tts > 0
            tts_median = float(np.median(f0_tts[tts_voiced])) if np.sum(tts_voiced) > 0 else ref_median
            anchor_pitch = float(ref_median)

            target_pitch_hz = anchor_pitch * (2.0 ** (mapped_semitones / 12.0))
            target_pitch_hz = np.clip(target_pitch_hz, 65.0, 480.0)

            # 3b. Morph vocal tract formants & throat resonance to match original speaker
            try:
                y_ref_raw, sr_ref = sf.read(temp_ref_wav)
                y_tts_raw, sr_tts = sf.read(synthesized_audio_path)
                c_ref = float(np.mean(librosa.feature.spectral_centroid(y=y_ref_raw, sr=sr_ref)[0]))
                c_tts = float(np.mean(librosa.feature.spectral_centroid(y=y_tts_raw, sr=sr_tts)[0]))
                formant_shift = float(np.clip(c_ref / max(100.0, c_tts), 0.82, 1.22))

                # Apply Praat Vocal Tract & Formant Transformation
                snd_morphed = call(snd_tts, "Change gender", 70.0, 500.0, formant_shift, anchor_pitch, 1.25, 1.0)
                snd_tts = snd_morphed
                dur_tts = snd_tts.duration
                pitch_tts = snd_tts.to_pitch(pitch_floor=75.0, pitch_ceiling=500.0)
                t_tts = pitch_tts.xs()
                f0_tts = pitch_tts.selected_array['frequency']

                # Recompute mapped pitch targets with updated time grid
                t_tts_norm = (t_tts - t_tts[0]) / max(1e-5, (t_tts[-1] - t_tts[0]))
                if np.sum(voiced_mask) > 1:
                    mapped_semitones = np.interp(t_tts_norm, t_voiced_norm, semitones_voiced)
                    mapped_semitones = gaussian_filter1d(mapped_semitones, sigma=1.5) * pitch_expressiveness
                else:
                    mapped_semitones = np.zeros_like(t_tts)
                target_pitch_hz = anchor_pitch * (2.0 ** (mapped_semitones / 12.0))
                target_pitch_hz = np.clip(target_pitch_hz, 65.0, 480.0)
            except Exception:
                pass

            # 4. Inject Dynamic PitchTier using Praat PSOLA
            manip = call(snd_tts, "To Manipulation", 0.01, 70.0, 500.0)
            pt = call("Create PitchTier", "expressive_pitch", 0.0, dur_tts)

            # Only add pitch points where the base TTS audio is voiced.
            # This preserves natural unvoiced consonants (s, t, p, k, sh) and breath pauses,
            # eliminating any robotic buzz or vocoder artifacts.
            for t_val, f_val, f_orig in zip(t_tts, target_pitch_hz, f0_tts):
                if f_orig > 0:
                    call(pt, "Add point", float(t_val), float(f_val))

            call([manip, pt], "Replace pitch tier")
            resynth_sound = call(manip, "Get resynthesis (overlap-add)")

            temp_psola_wav = output_audio_path.replace(".wav", "_temp_psola.wav")
            resynth_sound.save(temp_psola_wav, "WAV")

            # 5. Apply Dynamic Loudness (RMS Energy) Envelope Modulation
            y_tts, sr = sf.read(temp_psola_wav)
            y_ref, _ = sf.read(temp_ref_wav)

            hop = int(0.010 * sr)
            win = int(0.025 * sr)
            rms_ref = librosa.feature.rms(y=y_ref, frame_length=win, hop_length=hop)[0]
            rms_tts = librosa.feature.rms(y=y_tts, frame_length=win, hop_length=hop)[0]

            t_ref_rms = np.linspace(0, 1, len(rms_ref))
            t_tts_rms = np.linspace(0, 1, len(rms_tts))
            mapped_rms = np.interp(t_tts_rms, t_ref_rms, rms_ref)
            mapped_rms = gaussian_filter1d(mapped_rms, sigma=4)

            # Gain ratio with dynamic range exponent
            gain_curve = (mapped_rms + 1e-4) / (rms_tts + 1e-4)
            gain_curve = np.clip(gain_curve ** energy_expressiveness, 0.40, 2.20)

            t_frames = np.linspace(0, len(y_tts), len(gain_curve))
            t_samples = np.arange(len(y_tts))
            sample_gain = np.interp(t_samples, t_frames, gain_curve)

            y_modulated = y_tts * sample_gain
            
            # Match the authentic original speaker's average energy and headroom
            ref_rms_val = np.sqrt(np.mean(y_ref ** 2))
            mod_rms_val = np.sqrt(np.mean(y_modulated ** 2))
            if mod_rms_val > 1e-4 and ref_rms_val > 1e-4:
                target_scale = ref_rms_val / mod_rms_val
                y_modulated = y_modulated * target_scale
            
            peak = np.max(np.abs(y_modulated))
            if peak > 0.95:
                y_modulated = y_modulated * (0.92 / peak)

            sf.write(output_audio_path, y_modulated.astype(np.float32), sr)
            print(f"[DynamicProsody] Transferred dynamic pitch melody ({np.min(target_pitch_hz):.1f}–{np.max(target_pitch_hz):.1f} Hz) and loudness dynamics -> {output_audio_path}")

        finally:
            for p in [temp_ref_wav, output_audio_path.replace(".wav", "_temp_psola.wav")]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        return output_audio_path


_global_prosody_morpher: Optional[DynamicProsodyMorpher] = None

def get_dynamic_prosody_morpher() -> DynamicProsodyMorpher:
    global _global_prosody_morpher
    if _global_prosody_morpher is None:
        _global_prosody_morpher = DynamicProsodyMorpher()
    return _global_prosody_morpher
