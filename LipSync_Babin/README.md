<!-- markdownlint-disable -->

# Nativox LipSync_Babin Pipeline: Zero-API Multilingual Video Dubbing & Performance Transfer

> **Universal, Free & Autonomous AI Video Dubbing**: The **LipSync_Babin pipeline** dubs English talking-head videos into natural **Hindi (`hi`)** and **Bengali (`bn`)** with **1:1 Video Duration Synchronization**, **Continuous Background Music (BGM) Preservation**, **Speaker Vocal Timbre/Pitch Cloning**, and **High-Definition Sub-Nasal Lip Sync**—**operating 100% Free with ZERO API Keys required**.  
> **Creator & Lead Architect**: Babin Bid  

---

## 🌟 Key Features & Unique Selling Points (USP)

1. **100% Free / Zero API Key Architecture**:
   - **No subscriptions, credit cards, or external API keys needed**.
   - The primary LipSync_Babin pipeline utilizes local OpenAI Whisper for ASR, public Google GTX / Deep-Translator for colloquial Indic translation, Microsoft Edge-TTS for native neural speech synthesis, and local Praat PSOLA / OpenVoice V2 for speaker voice timbre transfer.
   - Optional Sarvam AI support is retained as a secondary fallback.
2. **True Speaker Voice Identity Transfer**:
   - Analyzes the original speaker's fundamental pitch ($F_0$), vocal tract formant resonance ($F_1, F_2, F_3$), and spectral centroid.
   - Morphs synthesized Indic speech to carry the **original speaker's exact vocal weight, throat resonance, and pitch contour** while articulating with native Hindi and Bengali phonetics.
3. **Continuous Background Music & Acoustic Environment Preservation**:
   - Uses **Meta HTDemucs** neural stem separation to disentangle speech from room tone, ambient reverberation, sound effects, and background music.
   - Mixes the dubbed dialogue back over the continuous BGM track, preventing silence gaps or jarring acoustic transitions.
4. **Sub-Nasal Selective Compositing & HD Restoration (GFPGAN)**:
   - Uses a dynamic 468-point 3D MediaPipe facial mesh to isolate only the lower lip boundary.
   - Keeps 100% of non-mouth pixels (**eyes, gaze, eyebrows, nose bridge, forehead skin pores, hair, and camera background**) pixel-identical to the original recording.
   - Restores mouth, lips, and teeth micro-textures using **GFPGAN v1.4**.
5. **Exact 1:1 Video Duration & Timeline Match**:
   - Enforces syllable-budgeted translation (~3.0 syllables/sec).
   - Precision pitch-invariant `atempo` duration alignment locks audio duration to the exact video timeline.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Windows 10/11 or Linux
- Python 3.10 / 3.11
- FFmpeg installed and available on system `PATH`

### 2. Environment Setup
```powershell
# 1. Clone / Navigate to repository
cd LipSync_Babin

# 2. Create and activate virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
pip install edge-tts deep-translator
```

### 3. Configuration (`.env`)
By default, Nativox runs in **Zero-API Mode** with no keys needed:
```ini
NATIVOX_DEVICE=cpu
NATIVOX_TTS=free
# Optional Sarvam API key (leave blank to run 100% free with Zero API Keys)
SARVAM_API_KEY=
WAV2LIP_REPO=/path/to/Wav2Lip
WAV2LIP_CHECKPOINT=/path/to/Wav2Lip/checkpoints/wav2lip_gan.pth
```

---

## 💻 Running the LipSync_Babin Pipeline

### Option A: Interactive Web UI (Recommended)
1. Launch the web server:
   ```powershell
   cd LipSync_Babin
   .\.venv\Scripts\python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 7865
   ```
2. Open your web browser at:
   👉 **`http://127.0.0.1:7865`**
3. Drag and drop any talking-head `.mp4` video.
4. Choose target language (**Hindi** or **Bengali**).
5. Voice Backend defaults to **`Primary Zero-API Mode (Edge-TTS + Tone Transfer) [100% Free / No Keys]`**.
6. Click **Dub Video Now** to watch live progress and view the final video in the integrated player.

### Option B: Command-Line Interface (CLI)

```powershell
# Navigate to directory
cd LipSync_Babin

# Run 100% Free Zero-API LipSync_Babin Pipeline (Hindi):
.\.venv\Scripts\python.exe pipeline.py --input testcases/test2.mp4 --lang hi --tts free --preserve-bgm --output outputs/test2_Hindi_Dubbed.mp4

# Run 100% Free Zero-API LipSync_Babin Pipeline (Bengali):
.\.venv\Scripts\python.exe pipeline.py --input testcases/test4.mp4 --lang bn --tts free --preserve-bgm --output outputs/test4_Bengali_Dubbed.mp4
```

### CLI Parameters:
| Flag | Options | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input` | `.mp4` path | *Required* | Path to input talking-head video |
| `--lang` | `hi`, `bn` | *Required* | Target dubbed language |
| `--output` | `.mp4` path | *Required* | Output destination file path |
| `--tts` | `free`, `edgetts`, `sarvam` | `free` | Speech synthesis provider (`free` requires 0 keys) |
| `--preserve-bgm`| boolean flag | `True` | Runs Demucs neural separation to keep BGM |
| `--enhance` | boolean flag | `True` | Runs GFPGAN + Selective Compositor |

---

## 📁 Repository Directory Structure

```
LipSync_Babin/
├── .env.example               # Universal environment template
├── ARCHITECTURE.md            # Mermaid system diagrams & architectural workflows
├── INSTRUCTIONS.md            # Comprehensive module-by-module working principles
├── README.md                  # Project overview & running syntax
├── config.py                  # Pydantic configuration schemas
├── pipeline.py                # Master CLI orchestration pipeline
├── requirements.txt           # Python package dependencies
│
├── speech_analysis/           # Speaker Performance Transfer Engine (SPTE)
│   ├── spm/                   # Acoustic, pitch, and facial analysis modules
│   └── transfer_engine.py     # High-level SPTE interface
│
├── synthesis/                 # Neural speech synthesis & voice transfer
│   ├── edgetts_adapter.py     # Microsoft Edge-TTS Zero-Key provider
│   ├── sarvam_adapter.py      # Sarvam Indic Bulbul provider (Optional fallback)
│   ├── tone_transfer_bridge.py# Praat PSOLA formant and timbre morphing bridge
│   └── tts_provider.py        # Abstract TTS provider base class
│
├── translation/               # Transcription and linguistic adaptation
│   ├── translator.py          # Local Whisper / Google GTX translation
│   └── syllable_translator.py # Syllable-budgeted duration translator
│
├── alignment/                 # Forced alignment & viseme mapping
├── lipsync/                   # Neural mouth synchronization
│   ├── wav2lip_engine.py      # Audio-conditioned Wav2Lip GAN generator
│   └── face_enhancer_bridge.py# GFPGAN super-resolution + selective mask
│
├── utils/                     # Audio, video, and alignment utilities
│   ├── audio_utils.py         # Demuxing and amix background mixing
│   ├── audio_separator_bridge.py # Meta HTDemucs neural stem separation
│   ├── duration_aligner.py    # Sample-accurate atempo audio alignment
│   └── video_utils.py         # FFprobe metadata extraction
│
├── web/                       # FastAPI web application
│   ├── app.py                 # REST backend and file streaming
│   └── templates/index.html   # Responsive HTML5 web dashboard
│
├── outputs/                   # Rendered dubbed video results
├── testcases/                 # Benchmark talking-head video samples
└── work/                      # Intermediate stem caches and feature arrays
```
