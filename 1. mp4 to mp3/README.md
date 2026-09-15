# Stage 1: Audio Extractor & Stem Separator

## High-Fidelity MP4 to MP3 Demuxing & Stem Isolation Service

Part of the **Nativox** AI Multilingual Dubbing Suite.

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 2](https://img.shields.io/badge/Next_Stage-Stage_2:_ASR-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../2.%20mp3%20to%20Text/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## 📖 Operational Overview

Stage 1 is the primary audio extraction gate for the Nativox pipeline. It ingests video content, renders a live playback preview in the browser, and extracts the pristine audio track into high-bitrate MP3 format using an asynchronous FFmpeg worker.

The extracted MP3 serves as the clean acoustic input for **Stage 2 (Automatic Speech Recognition & Formant Analysis)**.

---

## 🛠️ Tech Stack & Key Features

- **Backend:** FastAPI (Python 3.11 asynchronous server) + FFmpeg binary subprocess
- **Audio Codec:** `libmp3lame` variable/high-quality VBR encoding (`-q:a 2`, ~190 kbps)
- **Frontend:** Responsive vanilla HTML5, CSS3 glassmorphism, and modern JavaScript with dual side-by-side synchronized media players
- **Storage Management:** Segregated temp upload staging with automatic session isolation

---

## 📋 Prerequisites & Requirements

- **Python:** **3.11** (Repository pinned via root `.python-version`)
- **FFmpeg:** Required on system PATH:
  - **Windows (winget):** `winget install Gyan.FFmpeg`
  - **macOS (Homebrew):** `brew install ffmpeg`
  - **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install -y ffmpeg`
- Verify installation in your terminal:

  ```bash
  ffmpeg -version
  ```

---

## 🚀 Setup & Execution

### 1. Navigate to Backend Directory

```bash
cd "1. mp4 to mp3/backend"
```

### 2. Create & Activate Virtual Environment

- **Create Environment (Python 3.11):**

  ```bash
  python -m venv venv
  ```

- **Activate on Windows (PowerShell):**

  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

- **Activate on Windows (CMD):**

  ```cmd
  venv\Scripts\activate.bat
  ```

- **Activate on macOS / Linux / Git Bash:**

  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies & Launch Server

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

The web dashboard will be available at: **`http://127.0.0.1:8000`**

> [!IMPORTANT]
> **Access via `http://127.0.0.1:8000`, not raw `index.html`:**
> The FastAPI backend serves `frontend/index.html` directly on port `8000`. Opening `index.html` directly via file protocol (`file:///...`) will trigger browser CORS restrictions that prevent network requests to `/extract`.

---

## 🏛️ Pipeline Architecture

```mermaid
graph LR
    A["Input Video (.mp4 / .mov / .mkv)"] --> B["POST /extract"]
    B --> C["FFmpeg Subprocess (libmp3lame)"]
    C --> D["High-Quality MP3 File"]
    D --> E["Browser Audio Player & Download"]
    D -.-> F["Input to Stage 2 (ASR)"]

    linkStyle default stroke:#0284C7,stroke-width:2.5px;
```

---

## 🔌 API Reference

### `POST /extract`

Extracts audio from uploaded video payload.

- **Content-Type:** `multipart/form-data`
- **Body Parameter:** `file` (Binary video file)
- **Response:**

  ```json
  {
    "status": "success",
    "filename": "audio_1710482000.mp3",
    "download_url": "/audio/audio_1710482000.mp3",
    "duration_seconds": 42.8
  }
  ```

### `GET /audio/{filename}`

Streams the extracted MP3 audio file with range requests for seeking.

---

## 📁 Project Structure

```text
1. mp4 to mp3/
├── README.md               # Stage documentation
├── backend/
│   ├── main.py             # FastAPI REST endpoints & FFmpeg subprocess executor
│   └── requirements.txt    # FastAPI, Uvicorn, Python-Multipart
├── frontend/
│   └── index.html          # Dual-player side-by-side UI
└── storage/
    ├── uploads/            # Temporary incoming video files
    └── outputs/            # Transcoded audio output files
```

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

---

<p align="center">
  <a href="../README.md">🏠 Back to Suite Overview</a> &bull; <a href="../ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="../INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="../ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Module 1 Documentation</b></sub>
</p>
