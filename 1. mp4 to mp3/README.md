# MP4 → MP3 Extractor

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 2](https://img.shields.io/badge/Next_Stage-Stage_2:_ASR-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../2.%20mp3%20to%20Text/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)

---

A lightweight, full-stack microservice: upload a video file, preview it on the left, and extract its untouched raw audio track as an MP3 on the right. This is the standalone implementation of **Stage 1 (Audio Extraction)** from the Nativox dubbing pipeline.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python) + FFmpeg
- **Frontend:** Single-page HTML5/CSS/Vanilla JS with side-by-side video/audio preview (served directly by FastAPI)

---

## 📋 Requirements

- **Python:** 3.10 or 3.11 recommended
- **FFmpeg:** Installed and available on your system PATH:
  - **Windows:** `winget install Gyan.FFmpeg`
  - **macOS:** `brew install ffmpeg`
  - **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install -y ffmpeg`

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

Once running, navigate to: **`http://127.0.0.1:8000`**

---

## ⚙️ Manual Setup

### Windows PowerShell

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### Git Bash (Windows)

```bash
cd backend
py -3.11 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### macOS / Linux

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8000
```

---

## 🔄 How It Works

1. **Upload & Preview:** Drop a video file (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.m4v`). The browser immediately loads a live preview in the left player.
2. **Audio Isolation:** The frontend sends a `POST` request to `/extract`.
3. **FFmpeg Processing:**

   ```bash
   ffmpeg -i input.mp4 -vn -acodec libmp3lame -q:a 2 output.mp3
   ```

4. **Playback & Export:** The MP3 stream is loaded into the player on the right with a one-click download button.

---

## 📁 Project Structure

```text
1. mp4 to mp3/
├── README.md
├── run.bat
├── run.sh
├── backend/
│   ├── main.py            # FastAPI endpoints + FFmpeg subprocess executor
│   └── requirements.txt   # FastAPI, Uvicorn, Python-Multipart
├── frontend/
│   └── index.html         # Responsive side-by-side preview interface
└── storage/
    ├── uploads/           # Temp video storage (cleaned up automatically)
    └── outputs/           # Extracted MP3 audio files
```
