<!-- markdownlint-disable -->

# 🎙️ Stage 08 — Acoustic Voice Extraction, Profiling & Cloned Translation

## Overview
**Stage 08** is Nativox's dedicated research module for acoustic characterization and speaker voice profiling. It analyzes dialogue audio to extract:
- **Pitch Dynamics ($F_0$):** Mean, median, minimum, maximum, standard deviation, and dynamic pitch range.
- **Formant Resonances & Vocal Quality:** Vocal tract resonant formants ($F_1, F_2, F_3$), jitter (pitch perturbation), shimmer (amplitude perturbation), and Harmonics-to-Noise Ratio (HNR) via Praat/Parselmouth algorithms.
- **Spectral Timbre:** Spectral centroid, bandwidth, rolloff, flatness, zero-crossing rate, and 13 Mel-Frequency Cepstral Coefficients (MFCCs).
- **Rhythm & Cadence:** Speaking rate, articulation tempo, and pause-to-speech ratio.
- **Speaker Embedding & Emotion Tone:** Speaker identity vector and acoustic emotional heuristics.

It saves a normalized reference audio (`voice_profile_reference.wav`) alongside a comprehensive JSON schema (`voice_profile.json`).

---

## Architecture & How It Works

Stage 08 operates in two steps:
1. **`main.py` (Voice Profiling):** Analyzes speaker dialogue audio to extract the speaker's vocal characteristics and saves `voice_profile.json` and `voice_profile_reference.wav`.
2. **`test_translate.py` (Cloned Translation):** Translates input text into the target language and synthesizes speech using Coqui XTTS v2 conditioned on `voice_profile_reference.wav`, matching the pitch and loudness of the original speaker.

---

## Usage

### 1. Extract Voice Profile
From repository root:
```bash
cd Dubbing/08_Voice_extraction_translation
python main.py
```
*(Optionally specify an audio/video target via `python main.py tests/test2.mp4` or by editing `AUDIO_PATH` in `main.py`)*

### 2. Cloned Translation Synthesis
From repository root:
```bash
cd Dubbing/08_Voice_extraction_translation
python test_translate.py
```
*(Edit `INPUT_TEXT` and `TARGET_LANG` like `hi`, `es`, `fr`, etc. in `test_translate.py`)*
> **Note on Languages:** Coqui XTTS v2 supports `hi`, `en`, `es`, `fr`, `de`, `it`, `pt`, `pl`, `tr`, `ru`, `nl`, `cs`, `ar`, `zh-cn`, `ja`, `hu`, and `ko`. (XTTS does not support Bengali).
