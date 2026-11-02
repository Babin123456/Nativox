<!-- markdownlint-disable MD033 MD041 -->

<div align="center">

# 🎙️ NATIVOX

## *Modular Real-Time AI Multilingual Dubbing & Audiovisual Lip-Sync Suite*

<p align="center">
  <a href="https://github.com/sagnikkkkkkkk/Nativox/stargazers"><img src="https://img.shields.io/github/stars/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=apachespark&color=F59E0B" alt="GitHub Stars" /></a>
  <a href="https://github.com/sagnikkkkkkkk/Nativox/network/members"><img src="https://img.shields.io/github/forks/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=git&color=6366F1" alt="GitHub Forks" /></a>
  <a href="https://github.com/sagnikkkkkkkk/Nativox/issues"><img src="https://img.shields.io/github/issues/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=gitbook&color=EC4899" alt="Open Issues" /></a>
  <a href="https://github.com/sagnikkkkkkkk/Nativox/graphs/contributors"><img src="https://img.shields.io/github/contributors/sagnikkkkkkkk/Nativox?style=for-the-badge&logo=github&color=10B981" alt="Contributors" /></a>
  <a href="https://www.python.org/downloads/release/python-3119/"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
</p>

<p align="center">
  <a href="Dubbing/ARCHITECTURE.md"><b>📐 Technical Architecture</b></a> &nbsp;&bull;&nbsp;
  <a href="Dubbing/INSTRUCTIONS.md"><b>📖 Step-by-Step Instructions</b></a> &nbsp;&bull;&nbsp;
  <a href="Dubbing/ROADMAP.md"><b>🗺️ Research Roadmap</b></a> &nbsp;&bull;&nbsp;
  <a href="Lipsync/README.md"><b>👄 Lip-Sync Evaluation</b></a> &nbsp;&bull;&nbsp;
  <a href="Dubbing/00_Auto_Pip/README.md"><b>⚡ Automated Pipeline</b></a>
</p>

</div>

---

<h2 align="center">📖 Executive Summary</h2>

<p align="center">
  <b>Nativox</b> is an advanced AI-powered multilingual video dubbing and audiovisual synchronization suite.<br />
  It converts spoken source dialogue into natural, culturally fluent Indic speech (<b>Hindi and Bengali</b>)<br />
  with automated pitch/gender matching, dynamic speech pacing, voice cloning, and quantitative lip-sync evaluation.
</p>

<div align="center">

| 🎬 [Dubbing Engine](Dubbing/) | 👄 [Lip-Sync Suite](Lipsync/) |
| :---: | :---: |
| Automated & Modular Stages (00 → 08) | Computer Vision, Landmark Aperture & DTW |

</div>

---

<h2 align="center">🏛️ Top-Level Repository Architecture</h2>

<p align="center">
  <sub>Decoupled structure separating operational dubbing pipelines from independent computer-vision verification.</sub>
</p>

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

<h2 align="center">🚀 Quick Start Guide</h2>

<p align="center">
  <b>System Prerequisites:</b> Python 3.11 (strictly pinned) &bull; FFmpeg on <code>PATH</code> &bull; Git
</p>

<table align="center" width="100%">
  <tr>
    <th width="50%" align="center"><h3>⚡ Track A: Master Dubbing Pipeline</h3></th>
    <th width="50%" align="center"><h3>👄 Track B: Lip-Sync Evaluation Suite</h3></th>
  </tr>
  <tr>
    <td valign="top">
      <p align="center"><b>Windows (PowerShell)</b></p>

```powershell
cd Dubbing\00_Auto_Pip
python setup_env.py --create-venv
.\venv\Scripts\Activate.ps1
python main.py
```

  <p align="center"><b>Linux / macOS (Bash)</b></p>

```bash
cd Dubbing/00_Auto_Pip
python3 setup_env.py --create-venv
source venv/bin/activate
python main.py
```

  <p align="center">
    👉 <b><a href="http://127.0.0.1:8000">http://127.0.0.1:8000</a></b>
  </p>
    </td>
    <td valign="top">
      <p align="center"><b>Windows (PowerShell)</b></p>

```powershell
cd Lipsync\backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

  <p align="center"><b>Linux / macOS (Bash)</b></p>

```bash
cd Lipsync/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
```

  <p align="center">
    👉 <b><a href="http://127.0.0.1:8001">http://127.0.0.1:8001</a></b>
  </p>
    </td>
  </tr>
</table>

<br />

---

<h2 align="center">🗂️ Pipeline Breakdown (`Dubbing/`)</h2>

<div align="center">

| Stage | Module Name | Core Technology | Port | Purpose |
| :---: | :--- | :--- | :---: | :--- |
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

</div>

<br />

---

<h2 align="center">🔬 Lip-Sync Evaluation (`Lipsync/`)</h2>

<p align="center">
  Independent, non-intrusive quantitative evaluation comparing mouth motions against native speaker ground-truth:
</p>

<table align="center">
  <tr>
    <td align="center"><b>📍 Landmark Extraction</b><br />MediaPipe 468 3D mesh points</td>
    <td align="center"><b>📈 Aperture Dynamics</b><br />Normalized Mouth Aspect Ratio (MAR)</td>
    <td align="center"><b>⏱️ Temporal Synchronization</b><br />Dynamic Time Warping (DTW) & Lag (&tau;*)</td>
  </tr>
</table>

<br />

---

<h2 align="center">👥 Contributors & Academic Credits</h2>

<h3 align="center">Core Engineering Team</h3>

<p align="center">
  <a href="https://github.com/sagnikkkkkkkk/Nativox/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=sagnikkkkkkkk/Nativox" alt="Contributors" />
  </a>
</p>

<p align="center">
  <a href="https://github.com/Babin123456"><b>Babin Bid</b></a> &bull;
  <a href="https://github.com/rka2005"><b>Rohit Kumar Adak</b></a> &bull;
  <a href="https://github.com/sagnikkkkkkkk"><b>Sagnik Bachhar</b></a> &bull;
  <a href="https://github.com/Atanu2k4"><b>Atanu Saha</b></a>
</p>

<p align="center">
  <b>Faculty Guide:</b> Mr. Debjit Ghosh<br />
  <sub>Department of Computer Science & Engineering</sub>
</p>

<p align="center">
  <a href="Dubbing/LICENSE.md"><img src="https://img.shields.io/badge/License-MIT-3B82F6?style=flat-square&logo=open-source-initiative&logoColor=white" alt="License" /></a>
</p>
