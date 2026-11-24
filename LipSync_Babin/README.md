<!-- markdownlint-disable -->

# Nativox LipSync_Babin Pipeline: Zero-API Multilingual Video Dubbing & Performance Transfer

> **Universal, Free & Autonomous AI Video Dubbing**: The **LipSync_Babin pipeline** dubs English talking-head videos into natural **Hindi (`hi`)** and **Bengali (`bn`)** with **1:1 Video Duration Synchronization**, **Continuous Background Music (BGM) Preservation**, **Speaker Vocal Timbre/Pitch Cloning**, and **High-Definition Sub-Nasal Lip Sync**—**operating 100% Free with ZERO API Keys required**.  
> **Creator & Lead Architect**: Babin Bid  

---

## 🌟 Key Features & Unique Selling Points (USP)

1. **100% Free / Zero API Key Architecture**:
   - **No subscriptions, credit cards, or external API keys needed**.
   - Uses local OpenAI Whisper for ASR, Google GTX / Deep-Translator for colloquial Indic translation, Microsoft Edge-TTS for native neural speech synthesis, and Praat PSOLA / OpenVoice V2 for speaker voice timbre transfer.
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

## 🚀 Environment Setup & Python Configuration

### 1. Prerequisites
- **OS**: Windows 10/11, Ubuntu/Debian Linux, or macOS
- **Python**: Python 3.10 or 3.11 installed (Python 3.11 recommended)
- **FFmpeg**: Installed and available on system `PATH` (`ffmpeg -version`)
- **Git**: Installed on system `PATH`

---

### 2. Virtual Environment Setup

You can either create a dedicated `.venv` inside `LipSync_Babin` or share the unified virtual environment from `Dub_with_LipSync\venv`.

#### Method A: Dedicated Local Virtual Environment
Open PowerShell or your terminal in `LipSync_Babin`:

```powershell
# 1. Navigate to directory
cd D:\Projects\Nativox\LipSync_Babin

# 2. Create the virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (Command Prompt):
# .\.venv\Scripts\activate.bat
# Linux / macOS:
# source .venv/bin/activate

# 4. Upgrade pip and install wheel/setuptools
python -m pip install --upgrade pip setuptools wheel

# 5. Install PyTorch with CUDA (or CPU fallback)
# For NVIDIA GPUs:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# For CPU only:
# pip install torch torchvision torchaudio

# 6. Install all remaining pipeline requirements
pip install -r requirements.txt

# 7. Download neural weights (Wav2Lip GAN, GFPGAN v1.4, ResNet50 face detector)
python setup_models.py
```

> **Note on PowerShell Execution Policy**: If PowerShell blocks script activation, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```

#### Method B: Shared Environment (Dub_with_LipSync)
If you already have `Dub_with_LipSync\venv` configured with all dependencies, set the environment variable:

```powershell
# Windows (PowerShell):
$env:LIPSYNC_PYTHON = "D:\Projects\Nativox\Dub_with_LipSync\venv\Scripts\python.exe"

# Linux / macOS:
export LIPSYNC_PYTHON="/path/to/Nativox/Dub_with_LipSync/venv/bin/python"
```
The pipeline automatically detects and prioritizes `LIPSYNC_PYTHON`.

---

## 💻 Running the LipSync_Babin Pipeline

### Option A: Interactive Web UI (Recommended)

1. Launch the FastAPI web server:
   ```powershell
   cd D:\Projects\Nativox\LipSync_Babin
   .\.venv\Scripts\python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 7865
   ```
   *(Or using the shared venv: `D:\Projects\Nativox\Dub_with_LipSync\venv\Scripts\python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 7865`)*

2. Open your web browser at:
   👉 **`http://127.0.0.1:7865`**

3. Drag and drop any talking-head `.mp4` video.
4. Select the target language (**Hindi** or **Bengali**).
5. Voice Backend defaults to **`Primary Zero-API Mode (Edge-TTS + Tone Transfer) [100% Free / No Keys]`**.
6. Click **Dub Video Now** to observe real-time progress and stream the final synced video.

---

### Option B: Command-Line Interface (CLI)

```powershell
cd D:\Projects\Nativox\LipSync_Babin

# Run Zero-API Pipeline for Hindi (hi):
.\.venv\Scripts\python.exe pipeline.py --input testcases/test2.mp4 --lang hi --tts free --preserve-bgm --output outputs/test2_Hindi_Dubbed.mp4

# Run Zero-API Pipeline for Bengali (bn):
.\.venv\Scripts\python.exe pipeline.py --input testcases/test4.mp4 --lang bn --tts free --preserve-bgm --output outputs/test4_Bengali_Dubbed.mp4
```

### CLI Parameters:

| Flag | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input` | File path (`.mp4`) | *Required* | Path to input talking-head video |
| `--lang` | `hi`, `bn` | *Required* | Target dubbed language (`hi` = Hindi, `bn` = Bengali) |
| `--output` | File path (`.mp4`) | *Required* | Output destination file path |
| `--tts` | `free`, `edgetts`, `sarvam` | `free` | Speech synthesis provider (`free` operates without API keys) |
| `--preserve-bgm`| Flag | `True` | Runs Demucs neural separation to keep pristine background music |
| `--enhance` | Flag | `True` | Runs GFPGAN v1.4 super-resolution + selective sub-nasal compositing |
| `--work-dir` | Folder path | `work` | Directory for intermediate stems, spectrograms, and wav files |

---

## 🛠️ Troubleshooting & Common Fixes

### 1. `Permission denied: '.venv\Scripts\python.exe'`
- **Cause**: A background Python or Uvicorn process is still running and locking the file.
- **Fix**: Open PowerShell and kill the locking process:
  ```powershell
  Get-Process | Where-Object { $_.Path -like "*LipSync_Babin*" } | Stop-Process -Force
  ```

### 2. `AttributeError: module 'mediapipe' has no attribute 'solutions'`
- **Cause**: Mediapipe version 0.10.30+ changed landmark API structures.
- **Fix**: Ensure Mediapipe is pinned to an earlier release:
  ```powershell
  pip install "mediapipe<0.10.30"
  ```

### 3. Face Detection Truncation on Tight Portrait Videos
- **Cause**: Standard S3FD face detection inside Wav2Lip can truncate tight vertical portrait shots above the mouth line.
- **Fix**: Ensure `resize_factor=1` is used, or apply the MediaPipe FaceMesh bounding box extension included in the updated pipeline.

---

## 📁 Repository Directory Structure

```
LipSync_Babin/
├── ARCHITECTURE.md            # Mermaid system diagrams & architectural workflows
├── INSTRUCTIONS.md            # Module-by-module working principles & design notes
├── MATHEMATICAL_FOUNDATIONS.md# Acoustic formulas, PSOLA formant equations, metric loss
├── README.md                  # Master setup and execution guide
├── setup_models.py            # Automated neural models and weights downloader
├── config.py                  # Pipeline configuration schemas
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
│   ├── face_enhancer.py       # GFPGAN face restoration + SelectiveCompositor
│   ├── face_enhancer_bridge.py# Integration bridge for high-level pipeline
│   └── selective_compositor.py# 468-landmark sub-nasal mask and temporal blending
│
├── utils/                     # Audio, video, and environment utilities
│   ├── audio_utils.py         # Demuxing and amix background mixing
│   ├── audio_separator_bridge.py # Meta HTDemucs neural stem separation
│   ├── duration_aligner.py    # Sample-accurate atempo audio alignment
│   ├── env_utils.py           # Cross-platform Python discovery
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
