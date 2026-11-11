<!-- markdownlint-disable -->

# Nativox LipSync_Babin Pipeline: System Architecture & Technical Instructions

> **Creator & Lead Architect**: Babin Bid  
> This document provides a comprehensive breakdown of the working principles of every file in the **LipSync_Babin pipeline**, the exact end-to-end stages executed when a video is submitted via the Web UI or CLI, and the technologies utilized at each stage.

---

## 1. End-to-End LipSync_Babin Pipeline Processing Stages (Input Video $\rightarrow$ Output Dubbed Video)

When a user submits a talking-head video through the Web UI at `http://127.0.0.1:7860` (or `7865`), the LipSync_Babin pipeline executes the following 7 stages sequentially:

### Stage 1: Audio Extraction & Neural Stem Separation
- **Technology Required**: `FFmpeg`, `Meta HTDemucs` (`demucs.api` / `htdemucs_ft`), `PyTorch`, `SoundFile`
- **What Happens**:
  1. The input video is probed with `ffprobe` to extract exact duration, framerate, resolution, and presentation timestamps (PTS).
  2. The full master audio is extracted to `.wav`.
  3. Meta's hybrid transformer neural separator (`HTDemucs`) splits the master audio into two orthogonal stems:
     - `source_vocals.wav`: Pure, isolated speech (free of ambient noise or music).
     - `source_bgm.wav`: Continuous background music, room tone, and sound effects.

### Stage 2: Automatic Speech Recognition (ASR)
- **Technology Required**: `OpenAI Whisper` (Local Subprocess / CPU / PyTorch) with fallback to `Sarvam Saaras ASR`
- **What Happens**:
  1. The clean vocal track (`source_vocals.wav`) is fed into the local Whisper model.
  2. Generates the exact English spoken transcript with word-level timing anchors.
  3. Because this runs on local Whisper, **no API keys are consumed**.

### Stage 3: Syllable-Constrained Linguistic Adaptation
- **Technology Required**: `Google GTX Public Client` / `Deep-Translator` (Primary Zero-API) with fallback to `Sarvam 105B`
- **What Happens**:
  1. English and Indic languages have different expansion ratios (Hindi/Bengali text is naturally 20–30% longer than English).
  2. The `SyllableAwareTranslator` calculates the target speech budget:
     $$\text{Target Syllables} \approx \text{Duration (seconds)} \times 3.0\text{ syllables/sec}$$
  3. Translates the English transcript into colloquial Hindi or Bengali phrased to match the breath pacing of the original speaker.

### Stage 4: Neural Speech Synthesis & Speaker Performance Voice Transfer
- **Technology Required**: `Microsoft Edge-TTS` (Zero-API), `Parselmouth` (Praat C++ bindings), `OpenVoice V2`, `SciPy STFT/iSTFT`, `FFmpeg`
- **What Happens**:
  1. **Native Phonetic Synthesis**: Microsoft Edge-TTS synthesizes the translated text using native regional voices (`hi-IN-MadhurNeural`/`hi-IN-SwaraNeural` or `bn-IN-BashkarNeural`/`bn-IN-TanishaaNeural`). Gender is auto-detected from the original speaker's vocal track.
  2. **Pitch & Formant Profile Extraction**: The `ToneTransferBridge` analyzes the original speaker's fundamental pitch ($F_0$), pitch variation ($\sigma_{F0}$), and formants ($F_1, F_2, F_3$) via Burg's algorithm.
  3. **Timbre & Formant Transfer**: Praat PSOLA shifts the synthetic formant poles and dynamic pitch envelope to match the original speaker's vocal tract resonance without creating unnatural distortion.
  4. **Duration & Tempo Alignment**: Pitch-invariant FFmpeg `atempo` processing locks the speech duration to the millisecond timeline of the video.
  5. **Master Audio Mixing**: Dubbed dialogue is multiplexed with `source_bgm.wav` (`amix` filter) so the original room acoustics and music play continuously beneath the dialogue.

### Stage 5: Neural Lip Synchronization
- **Technology Required**: `Wav2Lip GAN`, `PyTorch`, `OpenCV`
- **What Happens**:
  1. The video frames and the synthesized master audio are passed to the Wav2Lip generator.
  2. The network predicts audio-conditioned mouth shapes (visemes) frame-by-frame, ensuring lip opening, jaw drops, and dental plosives match the Hindi/Bengali speech.

### Stage 6: Selective Sub-Nasal Compositing & HD Face Restoration
- **Technology Required**: `MediaPipe Face Mesh` (468 landmarks), `GFPGAN v1.4`, `OpenCV`, `NumPy`
- **What Happens**:
  1. **Sub-Nasal Masking**: Uses MediaPipe 3D face mesh to construct an elliptical mask strictly below the nasal columella (point 2) and mouth corners (points 61 & 291).
  2. **Identity Invariance**: The upper face (eyes, gaze, eyebrows, nose bridge, forehead skin, hair, and camera background) is kept 100% untouched from the original recording.
  3. **GFPGAN Super-Resolution**: Passes the lower mouth crop through GFPGAN v1.4 to restore sharp teeth boundaries, lip texture, and mucosal sheen.
  4. **Alpha Feathering**: Blends the restored mouth into the untouched original camera frame with a Gaussian falloff kernel ($\sigma = 5$).
  5. **Muxing**: Video and audio streams are muxed using FFmpeg (`libx264`, CRF 17).

### Stage 7: Quality Evaluation & Web Delivery
- **Technology Required**: `QualityEvaluator` (`librosa`, `parselmouth`, `cv2`), `FastAPI`
- **What Happens**:
  1. Audits audiovisual correlation (Mouth Aspect Ratio vs. audio RMS energy).
  2. Verifies that the audio voiced ratio exceeds 85% and background music is active.
  3. Delivers the final video to the Web UI video player and writes to `outputs/`.

---

## 2. Working Principles of Every File in the Codebase

### Root Directory
- **`pipeline.py`**:
  Master orchestration script. Coordinates all 7 stages from command-line arguments or Web UI triggers. Enforces Zero-API mode by default and manages data flow between audio stems, models, and output video muxers.
- **`config.py`**:
  Pydantic dataclass definitions validating configuration options, paths, target languages, and execution flags.
- **`requirements.txt`**:
  Explicit list of required Python libraries for audio processing, computer vision, web serving, and machine learning.
- **`.env` / `.env.example`**:
  Configuration file for device options (`cpu` / `cuda`) and optional fallback API keys.

---

### `translation/`
- **`translation/translator.py`**:
  Translation interface supporting Zero-API and API modes. Automatically runs local Whisper for speech-to-text when cloud keys are unset, and routes translation through Google GTX public endpoints and `deep-translator`.
- **`translation/syllable_translator.py`**:
  Calculates target syllable budgets based on audio duration and enforces colloquial phrasing so the translated dialogue naturally fits the speaker's breath pauses.
- **`translation/chunker.py`**:
  Utility for segmenting audio transcripts by utterance timestamps for long videos.

---

### `synthesis/`
- **`synthesis/edgetts_adapter.py`**:
  Primary zero-API neural voice synthesizer. Interfaces Microsoft Edge-TTS to generate high-fidelity Hindi and Bengali speech with automatic speaker gender detection.
- **`synthesis/sarvam_adapter.py`**:
  Secondary optional adapter for Sarvam AI Indic Bulbul TTS.
- **`synthesis/tone_transfer_bridge.py`**:
  Bridge script coordinating Praat PSOLA formant and timbre transfer, shifting generic TTS speech into the original speaker's vocal identity.
- **`synthesis/tts_provider.py`**:
  Abstract base class defining the required interface for all TTS synthesis adapters.
- **`synthesis/factory.py`**:
  Factory selector that instantiates the requested TTS adapter based on pipeline configuration.

---

### `speech_analysis/`
- **`speech_analysis/transfer_engine.py`**:
  High-level interface for the Speaker Performance Transfer Engine (SPTE), coordinating acoustic and facial tracking.
- **`speech_analysis/spm/tone_transfer.py`**:
  Core Praat PSOLA engine. Extracts fundamental pitch $F_0$, formants $F_1-F_3$, harmonics-to-noise ratio (HNR), and applies vocal tract length adjustments.
- **`speech_analysis/spm/facial_performance.py`**:
  Tracks 468 3D facial landmarks and head pose using MediaPipe.
- **`speech_analysis/spm/vocal_performance.py`**:
  Extracts acoustic feature matrices (jitter, shimmer, spectral centroid, RMS energy envelopes).
- **`speech_analysis/spm/quality_evaluator.py`**:
  Independent quality auditor that computes Mouth Aspect Ratio (MAR) vs. audio energy cross-correlation to verify lip-sync timing.
- **`speech_analysis/spm/performance_memory.py`**:
  Serializes and deserializes extracted speaker profiles to JSON and NumPy formats.

---

### `lipsync/`
- **`lipsync/wav2lip_engine.py`**:
  Wraps the Wav2Lip GAN model to generate mouth motions conditioned on target audio mel-spectrograms.
- **`lipsync/face_enhancer_bridge.py`**:
  Applies MediaPipe sub-nasal dynamic masking and GFPGAN v1.4 facial super-resolution to prevent blurring and preserve 100% of non-mouth facial details.

---

### `utils/`
- **`utils/audio_separator_bridge.py`**:
  Meta HTDemucs neural stem separation bridge. Splits master audio into clean speech dialogue and continuous BGM tracks.
- **`utils/audio_utils.py`**:
  FFmpeg audio extraction, channel conversion, and `amix` multiplexing routines.
- **`utils/duration_aligner.py`**:
  Sample-accurate duration aligner using pitch-invariant `atempo` filter chains to match dialogue to the exact video timeline.
- **`utils/video_utils.py`**:
  FFprobe diagnostic utility probing video duration, framerate, codec, and resolution.

---

### `web/`
- **`web/app.py`**:
  FastAPI web application exposing endpoints for video uploading, pipeline execution, and video streaming.
- **`web/templates/index.html`**:
  Responsive HTML5/CSS3 dashboard with drag-and-drop video upload, real-time logging terminal, and integrated video playback.
