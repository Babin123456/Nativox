# Nativox Manual & Operational Guide

Complete Architecture, Working Principles, and Module-by-Module Guide.

[![Suite Readme](https://img.shields.io/badge/Suite_Readme-📖_README.md-009688?style=for-the-badge&logo=readme&logoColor=white)](README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-3E8FC4?style=for-the-badge&logo=blueprint&logoColor=white)](ARCHITECTURE.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white)](ROADMAP.md)
[![MIT License](https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white)](LICENSE.md)

---

## 📑 Table of Contents

1. [Suite Overview & Modular Philosophy](#1-suite-overview--modular-philosophy)
2. [Module-by-Module Instructions](#2-module-by-module-instructions)
   - [Module 1: MP4 to MP3 Extraction (`1. mp4 to mp3/`)](#module-1-mp4-to-mp3-extraction-1-mp4-to-mp3)
   - [Module 2: MP3 to Text Transcription (`2. mp3 to Text/`)](#module-2-mp3-to-text-transcription-2-mp3-to-text)
   - [Module 3: Text to Keyword Extraction (`3. Text to Keyword/`)](#module-3-text-to-keyword-extraction-3-text-to-keyword)
   - [Module 4: Keyword Translation Engine (`4. Keyword Translate/`)](#module-4-keyword-translation-engine-4-keyword-translate)
3. [Running the Modular Suite](#3-running-the-modular-suite)
4. [Environment Setup & System Dependencies](#4-environment-setup--system-dependencies)

---

## 1. Suite Overview & Modular Philosophy

The **Nativox** suite divides video dubbing into clearly isolated research and operational modules. Each directory within `Nativox/` represents a self-contained microservice equipped with:

- An independent backend API (FastAPI)
- A dedicated interactive frontend
- Automation scripts (`run.bat` for Windows and `run.sh` for Git Bash / macOS / Linux)
- A stage-specific `README.md` explaining operational principles and API contracts

This structure allows researchers and evaluators to inspect, benchmark, and run every stage independently without coupling issues.

---

## 2. Module-by-Module Instructions

### Module 1: MP4 to MP3 Extraction (`1. mp4 to mp3/`)

- **Core Function:** Ingests video files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`) and extracts a clean, high-bitrate MP3 audio stream.
- **Working Principle:**
  - Invokes FFmpeg under the hood: `ffmpeg -i input.mp4 -vn -acodec libmp3lame -q:a 2 output.mp3`.
  - Discards video frames cleanly to minimize memory footprint.
- **Execution:**

  ```bash
  cd "1. mp4 to mp3"
  # Windows CMD / PowerShell
  .\run.bat
  # Git Bash / Linux / macOS
  ./run.sh
  ```

- **Port:** `http://127.0.0.1:8000`

---

### Module 2: MP3 to Text Transcription (`2. mp3 to Text/`)

- **Core Function:** Transcribes speech into timestamped text segments with high precision and acoustic speaker feature extraction.
- **Working Principle:**
  - Uses OpenAI's `whisper` / `faster-whisper` engine.
  - Generates millisecond-accurate start and end timestamps per sentence.
  - Analyzes audio pitch via `librosa` to classify speaker gender (`male` / `female`) for downstream voice assignment.
- **Execution:**

  ```bash
  cd "2. mp3 to Text"
  # Windows CMD / PowerShell
  .\run.bat
  # Git Bash / Linux / macOS
  ./run.sh
  ```

- **Port:** `http://127.0.0.1:8001`

---

### Module 3: Text to Keyword Extraction (`3. Text to Keyword/`)

- **Core Function:** Identifies salient keywords, key phrases, and technical terminology from the transcribed text.
- **Working Principle:**
  - Leverages `KeyBERT` and multilingual RAKE with Maximal Marginal Relevance (MMR) diversification.
  - Separates general conversational words from critical domain-specific entities.
- **Execution:**

  ```bash
  cd "3. Text to Keyword"
  # Windows CMD / PowerShell
  .\run.bat
  # Git Bash / Linux / macOS
  ./run.sh
  ```

- **Port:** `http://127.0.0.1:8002`

---

### Module 4: Keyword Translation Engine (`4. Keyword Translate/`)

- **Core Function:** Translates extracted keywords and domain entities across 15+ supported languages (Hindi, Bengali, Tamil, Telugu, Spanish, French, German, Japanese, etc.).
- **Working Principle:**
  - Employs `deep-translator` and domain glossary mapping with resilient fallback.
  - Ensures proper noun preservation and prevents literal translation errors on technical terms.
- **Execution:**

  ```bash
  cd "4. Keyword Translate"
  # Windows CMD / PowerShell
  .\run.bat
  # Git Bash / Linux / macOS
  ./run.sh
  ```

- **Port:** `http://127.0.0.1:8003`

---

## 3. Running the Modular Suite

To test all modules simultaneously, you can run each stage in a separate terminal:

| Terminal | Module | Windows Command | Git Bash / Linux Command | Local URL |
| :--- | :--- | :--- | :--- | :--- |
| **Terminal 1** | Stage 1 (MP4 to MP3) | `cd "1. mp4 to mp3" && .\run.bat` | `cd "1. mp4 to mp3" && ./run.sh` | `http://127.0.0.1:8000` |
| **Terminal 2** | Stage 2 (MP3 to Text) | `cd "2. mp3 to Text" && .\run.bat` | `cd "2. mp3 to Text" && ./run.sh` | `http://127.0.0.1:8001` |
| **Terminal 3** | Stage 3 (Text to Keyword) | `cd "3. Text to Keyword" && .\run.bat` | `cd "3. Text to Keyword" && ./run.sh` | `http://127.0.0.1:8002` |
| **Terminal 4** | Stage 4 (Keyword Translate) | `cd "4. Keyword Translate" && .\run.bat` | `cd "4. Keyword Translate" && ./run.sh` | `http://127.0.0.1:8003` |

> [!IMPORTANT]
> **Always access each stage through its local URL (`http://127.0.0.1:PORT`), NOT by opening raw `index.html` files!**
> - **Why raw `index.html` fails:** Double-clicking `index.html` opens it under the `file:///` protocol. Browsers restrict local file scripts from accessing relative API routes (e.g. `/extract`, `/api/transcribe`), triggering CORS or connection refused errors.
> - **How it works:** The FastAPI backend serves that exact `index.html` file over HTTP. Both the web UI and backend APIs run under the same origin.
> - **Do NOT delete `index.html`:** The FastAPI server dynamically reads and delivers `frontend/index.html` to your browser on root `/`. Deleting it will cause a `404 Not Found` or `FileNotFoundError`.

---

## 4. Environment Setup & System Dependencies

1. **Python 3.10 or 3.11:** Ensure Python is added to your system `PATH`.
2. **FFmpeg:** Required for audio extraction, duration-fitting, and remuxing.
   - **Windows:** `winget install Gyan.FFmpeg`
   - **macOS:** `brew install ffmpeg`
   - **Ubuntu/Debian:** `sudo apt update && sudo apt install -y ffmpeg`
