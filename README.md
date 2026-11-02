<!-- markdownlint-disable MD033 MD041 -->

<div align="center">

# 🎙️ NATIVOX

## *Modular Real-Time AI Multilingual Dubbing & Audiovisual Lip-Sync Suite*

<p align="center">
  <a href="https://github.com/sagnikkkkkkkk/Nativox/graphs/contributors"><img src="https://img.shields.io/github/contributors/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=github&color=009688" alt="Contributors" /></a>
  <a href="https://www.python.org/downloads/release/python-3119/"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="Dubbing/ARCHITECTURE.md"><img src="https://img.shields.io/badge/Architecture-Decoupled%20%26%20Modular-FF6B6B?style=for-the-badge&logo=blueprint&logoColor=white" alt="Modular Architecture" /></a>
  <a href="Dubbing/LICENSE.md"><img src="https://img.shields.io/badge/License-MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="License" /></a>
</p>

<p align="center">
  <a href="Dubbing/ARCHITECTURE.md"><img src="https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-3E8FC4?style=for-the-badge&logo=blueprint&logoColor=white" alt="Architecture" /></a>
  &nbsp;
  <a href="Dubbing/INSTRUCTIONS.md"><img src="https://img.shields.io/badge/Instructions-📖_INSTRUCTIONS.md-4FAE7A?style=for-the-badge&logo=googledocs&logoColor=white" alt="Instructions" /></a>
  &nbsp;
  <a href="Dubbing/ROADMAP.md"><img src="https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white" alt="Roadmap" /></a>
  &nbsp;
  <a href="Dubbing/LICENSE.md"><img src="https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="License" /></a>
</p>

</div>

---

## 📖 Executive Summary

**Nativox** is an AI-powered multilingual video dubbing and audiovisual synchronization suite. The project converts source video dialogue (such as English) into natural, culturally coherent Indic speech (Hindi and Bengali) with automated pitch/gender matching, speech pacing control, voice cloning, and quantitative lip-sync evaluation.

The repository is structured into two primary operational subsystems:

1. **[`Dubbing/`](Dubbing/)**: The end-to-end and modular video dubbing pipeline (Stages `00` through `08`).
2. **[`Lipsync/`](Lipsync/)**: The computer vision and signal processing evaluation service that quantifies lip movement, aperture dynamics, and temporal synchrony.

---

## 🏛️ Top-Level Repository Architecture

```text
Nativox/
├── Dubbing/                          # Complete Multilingual AI Dubbing Engine
│   ├── 00_Auto_Pip/                  # Master Orchestrator & Interactive Web Dashboard (Port 8000)
│   ├── 01_MP4_to_MP3/                # Video Demuxer & F0 Pitch Analysis (Port 8001)
│   ├── 02_MP3_to_Text/               # Whisper Speech-to-Text & VAD (Port 8002)
│   ├── 03_Text_to_Keyword/           # Salient Keyword & Entity Extractor (Port 8003)
│   ├── 04_Keyword_to_Sentence_.../   # Flan-T5 Sentence Reconstruction (Port 8004)
│   ├── 05a_Keyword_Translation_.../  # Research Terminology Translation (Port 8005)
│   ├── 05b_Sentence_Reformation.../  # SOV Grammar, Filler Removal & Précis (Port 8006)
│   ├── 06_Converted_Text_to_MP3/     # Edge Neural TTS Speech Synthesis (Port 8007)
│   ├── 07_Merge_MP3_with_MP4/        # Lossless Video Remuxer & Assembly (Port 8008)
│   ├── 08_Voice_extraction_.../      # Voice Profile Extraction & Cloned Translation
│   ├── ARCHITECTURE.md               # Technical Pipeline Architecture & Invariant Specifications
│   ├── INSTRUCTIONS.md               # Step-by-Step Execution Manual
│   └── ROADMAP.md                    # Project Evolution & Research Milestones
│
├── Lipsync/                          # Quantitative Lip-Sync Evaluation Suite
│   ├── backend/                      # FastAPI App, MediaPipe landmark extraction & DTW engine (Port 8001)
│   ├── frontend/                     # Interactive Video & Graph Comparison UI
│   ├── output/                       # Generated evaluation plots and side-by-side MP4s
│   ├── videos/                       # Cache for uploaded candidate videos
│   └── README.md                     # Lipsync Service Documentation
│
├── tests/                            # Controlled Benchmark & Calibration Test Videos
└── README.md                         # Main Suite Documentation (This File)
```

---

## 🚀 Quick Start Guide

### System Prerequisites

- **Operating System:** Windows, Linux, or macOS
- **Python:** 3.11 (strictly pinned across all modules)
- **FFmpeg:** Installed and available on your system `PATH` (required for media demuxing and remuxing)

---

### Track A: Run the Master Dubbing Pipeline (`00_Auto_Pip`)

To launch the automated end-to-end web dashboard that handles video upload, transcription, reformation, TTS generation, and final video assembly:

#### Windows (PowerShell) - Dubbing

```powershell
cd Dubbing\00_Auto_Pip
python setup_env.py --create-venv
.\venv\Scripts\Activate.ps1
python main.py
```

#### Linux / macOS (Bash) - Dubbing

```bash
cd Dubbing/00_Auto_Pip
python3 setup_env.py --create-venv
source venv/bin/activate
python main.py
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

---

### Track B: Run the Lip-Sync Evaluation Suite (`Lipsync`)

To evaluate the mouth-opening synchronization and cross-correlation between a ground-truth reference video and dubbed outputs:

#### Windows (PowerShell) - Lipsync

```powershell
cd Lipsync\backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

#### Linux / macOS (Bash) - Lipsync

```bash
cd Lipsync/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

Open your browser to:
👉 **`http://127.0.0.1:8001`**

---

## 🗂️ Pipeline Breakdown (`Dubbing/`)

| Stage | Module Name | Core Technology | Port | Purpose |
| :--- | :--- | :--- | :---: | :--- |
| **00** | **`00_Auto_Pip`** | FastAPI / Orchestrator | `8000` | Automated pipeline orchestrator and unified web UI; coordinates pitch detection, pacing, and assembly. |
| **01** | **`01_MP4_to_MP3`** | FFmpeg / Audio Demuxer | `8001` | Extracts audio stems and evaluates fundamental frequency ($F_0$) for voice gender identification. |
| **02** | **`02_MP3_to_Text`** | faster-whisper / Silero VAD | `8002` | Generates timestamped word- and segment-level speech transcripts. |
| **03** | **`03_Text_to_Keyword`** | Multilingual RAKE | `8003` | Extracts technical terminology and salient keywords from speech. |
| **04** | **`04_Keyword_to_Sentence`** | Google Flan-T5 / Seq2Seq | `8004` | Synthesizes full, grammatically well-formed sentences from keywords. |
| **05a** | **`05a_Keyword_Translation`** | deep-translator / Indic Trans | `8005` | Direct keyword and term translation *(research module, bypassed in automated pipeline)*. |
| **05b** | **`05b_Sentence_Reformation`** | Indic Grammar / Précis Engine | `8006` | Restructures English SVO to natural Indic SOV, strips fillers, and enforces speech budget. |
| **06** | **`06_Converted_Text_to_MP3`** | Microsoft Edge Neural TTS | `8007` | Synthesizes Hindi and Bengali speech with adaptive pitch and speech-rate scaling. |
| **07** | **`07_Merge_MP3_with_MP4`** | FFmpeg (`-c:v copy`) | `8008` | Losslessly replaces original audio with dubbed target audio into the final MP4 container. |
| **08** | **`08_Voice_extraction`** | Voice Profiling / Cloning | `8009` | Extracts speaker acoustic profiles for personalized voice conversion and translation. |

---

## 🔬 Lip-Sync Evaluation (`Lipsync/`)

The **Lipsync** module provides independent quantitative verification of dubbed videos:

- **Facial Landmark Tracking:** Detects upper/lower lip landmarks across all video frames with MediaPipe.
- **Mouth Aperture Curves:** Computes normalized vertical mouth opening profiles across time.
- **Signal Metrics:**
  - **Pearson Correlation ($r$):** Evaluates overall shape and articulation similarity.
  - **Dynamic Time Warping (DTW):** Measures non-linear temporal alignment.
  - **Lag Offset ($\tau^*$):** Identifies audio/visual sync delay in milliseconds ($\text{ms}$).
- **Visual Artifacts:** Automatically renders comparative temporal graphs and side-by-side composite review videos.

---

## 👥 Contributors & Academic Credits

### Core Contributors

<p align="center">
  <a href="https://github.com/sagnikkkkkkkk/Nativox/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=sagnikkkkkkkk/Nativox" alt="Contributors" />
  </a>
</p>

- **Student Contributors:**
  - [Babin Bid (@Babin123456)](https://github.com/Babin123456)
  - [Rohit Kumar Adak (@rka2005)](https://github.com/rka2005)
  - [Sagnik Bachhar (@sagnikkkkkkkk)](https://github.com/sagnikkkkkkkk)
  - [Atanu Saha (@Atanu2k4)](https://github.com/Atanu2k4)
- **Faculty Guide:** Mr. Debjit Ghosh (Department of Computer Science & Engineering)
- **License:** [MIT License](Dubbing/LICENSE.md)
