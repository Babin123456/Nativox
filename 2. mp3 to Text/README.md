# Nativox Transcribe — Audio to Text

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 1](https://img.shields.io/badge/Prev_Stage-Stage_1:_Extractor-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../1.%20mp4%20to%20mp3/README.md)
[![Stage 3](https://img.shields.io/badge/Next_Stage-Stage_3:_Keyword-FF6B6B?style=for-the-badge&logo=fastapi&logoColor=white)](../3.%20Text%20to%20Keyword/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)

---

A standalone speech-to-text (ASR) microservice for **English, Hindi, and Bengali**. Upload any audio file or video sound track, listen to the clip on the left, and view the clean transcribed text and timestamps on the right. This is the standalone implementation of **Stage 2 (ASR)** from the Nativox pipeline.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI + [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 build of OpenAI Whisper, CPU/GPU accelerated)
- **Frontend:** Single-page HTML5/CSS/Vanilla JS side-by-side player & transcript view (served directly by FastAPI)
- **Zero API keys:** Operates 100% locally with open-weights neural models.

---

## 📋 Requirements

- **Python:** **3.10 or 3.11** (Required: Python 3.14 lacks pre-compiled wheels for PyAV/faster-whisper)
- **Internet Connection:** Only required on the very first run to download model weights (cached locally in `~/.cache/huggingface/hub/` afterwards).

---

## 🚀 Quick Start

### Windows (Command Prompt / PowerShell)

```powershell
.\run.bat
```

### Git Bash (Windows) / macOS / Linux

```bash
chmod +x run.sh
./run.sh
```

Once running, navigate to: **`http://127.0.0.1:8001`**

> [!IMPORTANT]
> **Access via `http://127.0.0.1:8001`, not raw `index.html`:**
> The FastAPI backend serves `frontend/index.html` directly on port `8001`. Opening `index.html` directly as a `file:///` path causes browser CORS / connection errors with the `/api/transcribe` endpoint. Do **not** delete `frontend/index.html`, as FastAPI reads and delivers it upon connecting.

---

## ⚙️ Manual Setup

### Windows PowerShell

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
```

### Git Bash (Windows)

```bash
cd backend
py -3.11 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
```

### macOS / Linux

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8001
```

---

## 🔄 How It Works

1. **Audio Selection & Left Preview:** Drop an audio file (`.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`). The built-in audio player initializes immediately on the left.
2. **Language Selection:** Choose Auto-detect or lock to English, Hindi, or Bengali.
3. **Neural Transcription:** The file is posted to `/api/transcribe`. Faster-Whisper performs voice activity detection (VAD) and transcribes speech into timestamped tokens.
4. **Right Transcript Output:** Renders the text in proper Indic scripts (Devanagari or Bengali script), displays audio length, confidence %, and offers one-click copy and `.txt` download.

---

## 📁 Project Structure

```text
2. mp3 to Text/
├── README.md
├── run.bat
├── run.sh
├── backend/
│   ├── main.py              # FastAPI endpoints + serves frontend
│   ├── requirements.txt     # faster-whisper, fastapi, uvicorn, requests
│   └── app/
│       ├── config.py        # Model size (small/medium), upload caps
│       └── transcriber.py   # faster-whisper wrapper with LRU caching
└── frontend/
    └── index.html           # Side-by-side audio player & transcript UI
```
