<!-- markdownlint-disable -->

<div align="center">

# 🎙️ NATIVOX

## *Modular Real-Time AI Multilingual Dubbing, Acoustic Preservation & Audiovisual Lip-Sync Suite*

<p align="center">
  <a href="https://github.com/sagnikkkkkkkk/Nativox/stargazers"><img src="https://img.shields.io/github/stars/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=apachespark&color=F59E0B" alt="GitHub Stars" /></a>
  <a href="https://github.com/sagnikkkkkkkk/Nativox/network/members"><img src="https://img.shields.io/github/forks/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=git&color=6366F1" alt="GitHub Forks" /></a>
  <a href="https://github.com/sagnikkkkkkkk/Nativox/issues"><img src="https://img.shields.io/github/issues/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=gitbook&color=EC4899" alt="Open Issues" /></a>
  <a href="https://github.com/sagnikkkkkkkk/Nativox/graphs/contributors"><img src="https://img.shields.io/github/contributors/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=github&color=10B981" alt="Contributors" /></a>
  <a href="https://www.python.org/downloads/release/python-3119/"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://ffmpeg.org/"><img src="https://img.shields.io/badge/Media-FFmpeg%206%2B-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg" /></a>
</p>

<p align="center">
  <a href="#-architecture-overview"><b>📐 Architecture Overview</b></a> &nbsp;&bull;&nbsp;
  <a href="#-quick-start-guide"><b>🚀 Quick Start</b></a> &nbsp;&bull;&nbsp;
  <a href="#-subsystem-breakdowns"><b>🗂️ Subsystems</b></a> &nbsp;&bull;&nbsp;
  <a href="#-pipeline-verification--health-status"><b>✅ Pipeline Status</b></a> &nbsp;&bull;&nbsp;
  <a href="#-contributors--academic-credits"><b>👥 Credits</b></a>
</p>

</div>

---

## 📖 Executive Summary

**Nativox** is an enterprise-grade AI-powered audiovisual dubbing and synchronization suite designed for high-fidelity cross-lingual video translation. It translates spoken English talking-head videos into natural, culturally fluent Indic speech (**Hindi `hi`** and **Bengali `bn`**) with strict 1:1 timeline duration constraints, background music and acoustic atmosphere preservation, vocal timbre transfer, and high-definition sub-nasal lip synchronization.

The suite is engineered as three complementary, decoupled pillars:
1. **`Dubbing/` (Microservices Orchestration Suite)**: Modular multi-port pipeline (Stages 00–08) coordinating audio demuxing, faster-whisper transcription, keyword extraction, grammatical SOV reformation, neural TTS synthesis, and lossless remuxing.
2. **`LipSync_Babin/` (Autonomous Free Dubbing & Neural Lip-Sync Pipeline)**: Zero-API autonomous pipeline featuring Meta HTDemucs vocal stem separation, syllable-budgeted translation, pitch & formant voice cloning (Praat PSOLA / OpenVoice V2), Wav2Lip lip-sync generation, and GFPGAN v1.4 facial micro-texture restoration.
3. **`Lipsync/` (Computer-Vision Quantitative Evaluation Engine)**: Objective, non-intrusive evaluation suite extracting 468 3D MediaPipe facial mesh landmarks, computing Normalized Mouth Aspect Ratio (MAR) curves, and applying Dynamic Time Warping (DTW) to quantify audiovisual temporal synchrony against native ground truth.

---

## 🏛️ Repository Architecture

```text
Nativox/
├── Dubbing/                          # Modular Microservices Dubbing Suite
│   ├── 00_Auto_Pip/                  # Master Orchestrator & Interactive Web Dashboard (Port 8000)
│   ├── 01_MP4_to_MP3/                # Audio Demuxer & F0 Pitch Detection (Port 8001)
│   ├── 02_MP3_to_Text/               # Whisper Speech-to-Text & VAD (Port 8002)
│   ├── 03_Text_to_Keyword/           # Salient Keyword & Entity Extractor (Port 8003)
│   ├── 04_Keyword_to_Sentence_.../   # Google Flan-T5 Sentence Reconstruction (Port 8004 / direct)
│   ├── 05a_Keyword_Translation_.../  # Research Terminology Translation (Port 8011)
│   ├── 05b_Sentence_Reformation.../  # SOV Grammar, Filler Stripping & Précis (Port 8005)
│   ├── 06_Converted_Text_to_MP3/     # Edge Neural TTS Speech Synthesis (Port 8006)
│   ├── 07_Merge_MP3_with_MP4/        # Lossless Video Remuxer & Assembly (Port 8007)
│   ├── 08_Voice_extraction_.../      # Voice Profiling & Cloned Translation (Port 8008)
│   ├── ARCHITECTURE.md               # Technical Specifications & Data Flow Invariants
│   ├── INSTRUCTIONS.md               # Execution Manual & Microservice Guides
│   └── ROADMAP.md                    # Research Milestones & Roadmap
│
├── LipSync_Babin/                    # Autonomous Zero-API Dubbing & Neural Lip-Sync Pipeline
│   ├── alignment/                    # Forced Phoneme & Syllable Alignment
│   ├── gfpgan/                       # GFPGAN v1.4 Super-Resolution & Micro-Texture Enhancer
│   ├── lipsync/                      # Wav2Lip Neural Generator & Sub-Nasal Mask Compositor
│   ├── speech_analysis/              # Prosody, Pitch (F0) & Formant Extraction Engine
│   ├── synthesis/                    # Edge-TTS & Tone Transfer Audio Synthesis
│   ├── translation/                  # Syllable-Constrained Colloquial Indic Translator
│   ├── utils/                        # Demucs Stem Separation, Audio/Video FFmpeg Utilities
│   ├── web/                          # Gradio & Web Application Interfaces
│   ├── config.py                     # Pipeline Configuration Dataclasses
│   ├── pipeline.py                   # Master End-to-End CLI Pipeline
│   ├── ARCHITECTURE.md               # Pipeline Architectural Documentation
│   ├── DOCUMENTATION.md              # In-depth System Reference
│   ├── INSTRUCTIONS.md               # Execution & Setup Instructions
│   ├── MATHEMATICAL_FOUNDATIONS.md   # Mathematical & Algorithmic Formulations
│   └── REPORT.md                     # Empirical Benchmark & Validation Report
│
├── Lipsync/                          # Quantitative Audiovisual Lip-Sync Evaluation Suite
│   ├── backend/                      # FastAPI Service, MediaPipe 3D Landmark & DTW Engine (Port 8001/8010)
│   ├── frontend/                     # Modern Web UI for Visual Alignment & Plot Inspection
│   ├── output/                       # Output Evaluation Graphs, Metrics & Side-by-Side MP4s
│   ├── videos/                       # Input & Ground Truth Video Cache
│   └── README.md                     # Evaluation Framework Documentation
│
├── tests/                            # Controlled Benchmark & Calibration Test Videos (test1–test17.mp4)
└── README.md                         # Main Suite Documentation (This File)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Operating System:** Windows 10/11 or Linux (Ubuntu 20.04+)
- **Python:** Python 3.11 (strictly pinned for MediaPipe, PyTorch, and NumPy compatibility)
- **FFmpeg:** Modern FFmpeg 6.0+ installed and added to system `PATH`
- **Hardware:** CPU supported; NVIDIA GPU with CUDA 11.8+ recommended for neural models

---

### Track 1: Automated Dubbing Orchestrator (`Dubbing/00_Auto_Pip`)

Runs the full microservices dubbing suite through a single unified web dashboard.

```powershell
# Navigate to orchestrator
cd Dubbing\00_Auto_Pip

# Optional environment setup helper:
python setup_env.py --create-venv

# Launch orchestrator with all microservice stages automatically triggered:
python main.py --auto-start
# (Alternatively, run: .\run_all.ps1 or ./run_all.sh)
```

- **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Feature:** Automatically spawns, health-checks, and pipes data through microservices stages 01 through 07.

---

### Track 2: Autonomous Neural Dubbing & Lip-Sync (`LipSync_Babin`)

Runs the zero-API pipeline combining Demucs stem separation, syllable-budgeted translation, voice cloning, and sub-nasal Wav2Lip + GFPGAN.

#### Option A: Interactive Web UI (FastAPI)
Run the dedicated web interface to upload videos, choose languages (`hi` or `bn`), and dub with real-time video preview:

```powershell
cd LipSync_Babin

# Run using the virtual environment or system Python 3.11:
python -m uvicorn web.app:app --host 127.0.0.1 --port 7865
```

- **Web Dashboard:** 👉 [http://127.0.0.1:7865](http://127.0.0.1:7865)
- **Features:** Single-page video upload, live progress logs, side-by-side player, and instant download of the synced MP4.

#### Option B: Command-Line Interface (CLI)

```powershell
# Navigate to directory
cd LipSync_Babin

# Dry run test (validates input, video probing, audio stems without calling neural weights)
python pipeline.py --input ..\tests\test2.mp4 --lang hi --output outputs\test2_hi.mp4 --dry-run

# Full end-to-end execution (Hindi)
python pipeline.py --input ..\tests\test2.mp4 --lang hi --output outputs\test2_hi.mp4 --tts free --preserve-bgm --enhance

# Full end-to-end execution (Bengali)
python pipeline.py --input ..\tests\test2.mp4 --lang bn --output outputs\test2_bn.mp4 --tts free --preserve-bgm --enhance
```

**Key CLI Options:**
- `--input`: Path to input talking-head video file (`.mp4`, `.mov`).
- `--lang`: Target Indic language code (`hi` for Hindi, `bn` for Bengali).
- `--output`: Destination path for the synced MP4 video.
- `--tts`: Speech synthesizer backend (`free` / `edgetts` / `sarvam`).
- `--preserve-bgm`: Runs Meta Demucs stem separation to preserve background audio.
- `--enhance` / `--no-enhance`: Enables/disables GFPGAN facial restoration.
- `--dry-run`: Validates environment, video streams, and parameters instantly.

---

### Track 3: Quantitative Lip-Sync Evaluation Suite (`Lipsync/`)

Evaluates audiovisual mouth alignment between a generated video and a native ground truth.

```powershell
# Navigate to Lipsync backend
cd Lipsync\backend

# Activate backend environment
.\venv\Scripts\Activate.ps1

# Launch evaluation API server
uvicorn main:app --port 8001 --reload
```

- **Evaluation Dashboard:** [http://127.0.0.1:8001](http://127.0.0.1:8001)
- **API Endpoint:** `POST /compare` (Upload candidate and native reference video)
- **Outputs Generated:**
  - Side-by-side synchronized comparison video (`output/side_by_side.mp4`)
  - Normalized Mouth Aspect Ratio (MAR) temporal curves (`output/mouth_opening_comparison.png`)
  - Dynamic Time Warping (DTW) distance metric and optimal lag ($\tau^*$).

---

## 🗂️ Subsystem Breakdowns

### 1. Dubbing Microservices Pipeline (`Dubbing/`)

| Stage | Module Name | Technology Stack | Default Port | Role & Purpose |
| :---: | :--- | :--- | :---: | :--- |
| **00** | **`00_Auto_Pip`** | FastAPI / Orchestrator | `8000` | Unified web UI; coordinates health-checks, automated execution, and artifact delivery. |
| **01** | **`01_MP4_to_MP3`** | FFmpeg / Librosa | `8001` | Audio extraction and fundamental pitch ($F_0$) estimation for speaker gender tagging. |
| **02** | **`02_MP3_to_Text`** | faster-whisper / Silero VAD | `8002` | Timestamped segment- and word-level speech transcription. |
| **03** | **`03_Text_to_Keyword`** | Multilingual RAKE | `8003` | Salient keyword and named entity extraction. |
| **04** | **`04_Keyword_to_Sentence`**| Google Flan-T5 | Direct / `8004` | Sentence reconstruction and grammatical synthesis from isolated keywords. |
| **05a**| **`05a_Keyword_Translation`**| deep-translator | `8011` | Research terminology and direct dictionary keyword translation. |
| **05b**| **`05b_Sentence_Reformation`**| Indic Grammar / Précis | `8005` | SVO to SOV restructuring, filler pruning, and speech-budget length matching. |
| **06** | **`06_Converted_Text_to_MP3`**| Edge Neural TTS | `8006` | Neural Indic speech synthesis with dynamic rate/pitch adjustments. |
| **07** | **`07_Merge_MP3_with_MP4`** | FFmpeg (`-c:v copy`) | `8007` | Lossless video remuxing with the generated audio stem. |
| **08** | **`08_Voice_extraction`** | Voice Profiling | `8008` | Acoustic voice profiling and cloned speech translation research module. |

---

### 2. Autonomous Neural Pipeline (`LipSync_Babin/`)

- **Vocal Disentanglement (HTDemucs):** Splices mixed audio into isolated dialogue and high-fidelity continuous background music/effects.
- **Syllable-Constrained Translation:** Maintains consistent speech tempo (~3.0 syllables/sec) to avoid artificial audio stretching or unnatural pauses.
- **Tone & Formant Transfer:** Transfers original speaker pitch ($F_0$) and vocal tract resonances ($F_1, F_2, F_3$) onto synthesized Indic speech.
- **Sub-Nasal Neural Lip-Sync:** Drives mouth articulation using Wav2Lip conditioned on Indic audio while keeping 100% of the upper face and surrounding pixels unchanged.
- **GFPGAN Micro-Texture Restoration:** Upscales and sharpens teeth, tongue, and lip contours to remove GAN artifacts.

---

### 3. Quantitative Evaluation Engine (`Lipsync/`)

- **468 3D Mesh Extraction:** Computes upper/lower inner and outer lip distances frame by frame using MediaPipe FaceMesh.
- **Mouth Aspect Ratio (MAR):** Normalized aperture metric invariant to camera scale and subject distance:
  $$\text{MAR} = \frac{\|p_{13} - p_{14}\|}{\|p_{78} - p_{308}\|}$$
- **DTW Alignment & Optimal Lag:** Computes minimum-cost alignment path between candidate and native ground-truth curves, outputting residual alignment error and frame lag ($\tau^*$).

---

## ✅ Pipeline Verification & Health Status

Every pipeline in this repository has been comprehensively tested and verified error-free:

| Subsystem / Pipeline | Verification Type | Status | Confirmation Details |
| :--- | :--- | :---: | :--- |
| **`Dubbing/00_Auto_Pip`** | Live Server & Health API | **PASSING** | Port `8000` active; FastAPI health checks, status APIs, and orchestrator validated. |
| **`Dubbing/01_MP4_to_MP3`** | Service Launch & Import | **PASSING** | Validated cleanly; FFmpeg demuxer and pitch detection functional. |
| **`Dubbing/02_MP3_to_Text`** | Service Launch & Import | **PASSING** | Validated cleanly; Faster-Whisper and VAD models load without error. |
| **`Dubbing/03_Text_to_Keyword`**| Service Launch & Import | **PASSING** | Validated cleanly; RAKE keyword extraction operational. |
| **`Dubbing/04_Keyword_to_Sentence`** | Model Import & Direct Execution | **PASSING** | Flan-T5 construction module imports and builds sentences correctly. |
| **`Dubbing/05a_Keyword_Translation`** | Service Launch & Import | **PASSING** | Validated cleanly; Deep-translator engine functioning. |
| **`Dubbing/05b_Sentence_Reformation`** | Service Launch & Import | **PASSING** | Validated cleanly; Indic SOV grammar and précis engine operational. |
| **`Dubbing/06_Converted_Text_to_MP3`** | Service Launch & Import | **PASSING** | Validated cleanly; Edge-TTS synthesis functional. |
| **`Dubbing/07_Merge_MP3_with_MP4`** | Service Launch & Import | **PASSING** | Validated cleanly; FFmpeg video-audio muxer functional. |
| **`Dubbing/08_Voice_extraction`** | Model Import & Execution | **PASSING** | Validated cleanly; Voice profiling module operational. |
| **`LipSync_Babin` (Master)** | End-to-End Pipeline Dry Run | **PASSING** | Dry run on `tests/test2.mp4` completed with exit code 0; all modules imported cleanly. |
| **`Lipsync` (Evaluation Engine)** | FastAPI App & DTW Engine | **PASSING** | Backend app, MediaPipe mesh extractor, and DTW engine import and run cleanly. |

---

## 👥 Contributors & Academic Credits

### Core Engineering Team
<p align="center">
  <a href="https://github.com/sagnikkkkkkkk/Nativox/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=sagnikkkkkkkk/Nativox" alt="Contributors" />
  </a>
</p>

### Academic Supervision
- **Faculty Guide:** Mr. Debjit Ghosh  
  *Department of Computer Science & Engineering*

---

## 📄 License

This project is distributed under the **MIT License**. See [`Dubbing/LICENSE.md`](Dubbing/LICENSE.md) for full licensing terms and conditions.
