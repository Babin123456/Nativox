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
   - [Module 5: Sentence Reformation & Précis (`5. Sentence Reformation/`)](#module-5-sentence-reformation--précis-5-sentence-reformation)
   - [Module 6: Sentence Construction & Syntax Restoration (`6. Sectence Construction/`)](#module-6-sentence-construction--syntax-restoration-6-sectence-construction)
3. [Running the Modular Suite](#3-running-the-modular-suite)
4. [Environment Setup & System Dependencies](#4-environment-setup--system-dependencies)

---

## 1. Suite Overview & Modular Philosophy

The **Nativox** suite divides video dubbing and cross-lingual audio transformation into 6 clearly isolated research and operational modules. Each directory represents a self-contained microservice or deep-learning module equipped with:

- An independent backend API (FastAPI) or standalone training/inference engine
- A dedicated interactive frontend (Stages 1 through 5) or CLI suite (Stage 6)
- Independent virtual environment setup and execution procedures for Windows, macOS, and Linux
- A stage-specific `README.md` explaining operational principles and API contracts
- A pinned **Python 3.11** environment specification via the repository-wide `.python-version` file

This structure allows researchers and evaluators to inspect, benchmark, and run every stage independently without coupling issues.

---

## 2. Module-by-Module Instructions

### Module 1: MP4 to MP3 Extraction (`1. mp4 to mp3/`)

- **Core Function:** Ingests video files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`) and extracts a clean, high-bitrate MP3 audio stream.
- **Working Principle:**
  - Invokes FFmpeg asynchronously: `ffmpeg -i input.mp4 -vn -acodec libmp3lame -q:a 2 output.mp3`.
  - Discards video frames cleanly to minimize disk and memory footprint.
  - Serves a synchronized side-by-side video and audio preview in the browser.
- **Execution:**

  ```bash
  cd "1. mp4 to mp3/backend"
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8000
  ```

- **Port:** `http://127.0.0.1:8000`

---

### Module 2: MP3 to Text Transcription (`2. mp3 to Text/`)

- **Core Function:** Transcribes speech into timestamped text segments with high precision and acoustic speaker feature extraction.
- **Working Principle:**
  - Uses `faster-whisper` (CTranslate2 build of OpenAI Whisper) with Silero VAD.
  - Generates millisecond-accurate start and end timestamps per sentence.
  - Automatically identifies language and renders Indic scripts (Devanagari for Hindi, Bangla script for Bengali).
- **Execution:**

  ```bash
  cd "2. mp3 to Text/backend"
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8001
  ```

- **Port:** `http://127.0.0.1:8001`

---

### Module 3: Text to Keyword Extraction (`3. Text to Keyword/`)

- **Core Function:** Identifies salient keywords, key phrases, and technical terminology from the transcribed text.
- **Working Principle:**
  - Leverages multilingual **RAKE (Rapid Automatic Keyword Extraction)** with joint English, Hindi, and Bengali stopword elimination.
  - Scores words using co-occurrence frequency ($W_{\text{deg}} / W_{\text{freq}}$).
  - Classifies Unicode blocks (Latin, Devanagari, Bengali) for visual script proportion metering.
- **Execution:**

  ```bash
  cd "3. Text to Keyword/backend"
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8010
  ```

- **Port:** `http://127.0.0.1:8010`

---

### Module 4: Keyword Translation Engine (`4. Keyword Translate/`)

- **Core Function:** Translates extracted keywords and domain entities and generates phonetic pronunciation transliterations.
- **Working Principle:**
  - Employs `deep-translator` with failover resilience for technical terminology preservation.
  - Synthesizes readable Latin phonetic transliterations using `indic-transliteration` (ITRANS / Harvard-Kyoto).
  - Employs lightweight Unicode script detection to identify source scripts instantly.
- **Execution:**

  ```bash
  cd "4. Keyword Translate/backend"
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8011
  ```

- **Port:** `http://127.0.0.1:8011`

---

### Module 5: Sentence Reformation & Précis (`5. Sentence Reformation/`)

- **Core Function:** Disfluency cleaning, syntax restoration into meaningful Hindi, and strict 35%–40% paragraph précis compression.
- **Working Principle:**
  - Strips verbal fillers (*um, uh, basically, you know*) and restructures broken keywords or ASR speech into grammatically complete SOV Hindi sentences.
  - Analyzes transcript paragraphs from MP3 audio and algorithmically extracts an information-dense précis fitting strictly within 35%–40% of original word length:
    $$\lfloor 0.35 \times W_{\text{orig}} \rfloor \le W_{\text{precis}} \le \lceil 0.40 \times W_{\text{orig}} \rceil$$
- **Execution:**

  ```bash
  cd "5. Sentence Reformation/backend"
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8012
  ```

- **Port:** `http://127.0.0.1:8012`

---

### Module 6: Sentence Construction & Syntax Restoration (`6. Sectence Construction/`)

- **Core Function:** Learns canonical sentence syntax directly from PDF or Word documents and reconstructs broken/disordered sentences into fluent English.
- **Working Principle:**
  - Extracts clean reference sentences from `.pdf` or `.docx` documents using `pypdf` and `python-docx`.
  - Self-supervises training via synthetic noise generation (word jumbling, function word dropping, inflection distortion).
  - Fine-tunes a Google Flan-T5 Seq2Seq Transformer model using PyTorch and Hugging Face Transformers.
  - Provides an inference engine (`construct.py`) supporting interactive CLI testing, single-sentence inference, and batch file processing.
- **Execution:**

  ```bash
  cd "6. Sectence Construction"
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt

  # Train the Seq2Seq Transformer on PDF corpus
  python train.py

  # Interactive live CLI testing
  python construct.py
  ```

---

## 3. Running the Modular Suite

To test all modules simultaneously, you can run each stage in a separate terminal:

| Terminal | Module | Windows Command | Git Bash / Linux Command | Local URL / Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Terminal 1** | Stage 1 (MP4 to MP3) | `cd "1. mp4 to mp3/backend" && python -m uvicorn main:app --reload --port 8000` | `cd "1. mp4 to mp3/backend" && python -m uvicorn main:app --reload --port 8000` | `http://127.0.0.1:8000` |
| **Terminal 2** | Stage 2 (MP3 to Text) | `cd "2. mp3 to Text/backend" && python -m uvicorn main:app --reload --port 8001` | `cd "2. mp3 to Text/backend" && python -m uvicorn main:app --reload --port 8001` | `http://127.0.0.1:8001` |
| **Terminal 3** | Stage 3 (Text to Keyword) | `cd "3. Text to Keyword/backend" && python -m uvicorn main:app --reload --port 8010` | `cd "3. Text to Keyword/backend" && python -m uvicorn main:app --reload --port 8010` | `http://127.0.0.1:8010` |
| **Terminal 4** | Stage 4 (Keyword Translate) | `cd "4. Keyword Translate/backend" && python -m uvicorn main:app --reload --port 8011` | `cd "4. Keyword Translate/backend" && python -m uvicorn main:app --reload --port 8011` | `http://127.0.0.1:8011` |
| **Terminal 5** | Stage 5 (Sentence Reformation) | `cd "5. Sentence Reformation/backend" && python -m uvicorn main:app --reload --port 8012` | `cd "5. Sentence Reformation/backend" && python -m uvicorn main:app --reload --port 8012` | `http://127.0.0.1:8012` |
| **Terminal 6** | Stage 6 (Sentence Construction) | `cd "6. Sectence Construction" && python construct.py` | `cd "6. Sectence Construction" && python3 construct.py` | Interactive CLI |

> [!IMPORTANT]
> **Always access web stages through their local URL (`http://127.0.0.1:PORT`), NOT by opening raw `index.html` files!**
>
> - **Why raw `index.html` fails:** Double-clicking `index.html` opens it under the `file:///` protocol. Browsers restrict local file scripts from accessing relative API routes (e.g. `/extract`, `/api/transcribe`), triggering CORS or connection refused errors.
> - **How it works:** The FastAPI backend serves that exact `index.html` file over HTTP. Both the web UI and backend APIs run under the same origin.
> - **Do NOT delete `index.html`:** The FastAPI server dynamically reads and delivers `frontend/index.html` to your browser on root `/`. Deleting it will cause a `404 Not Found` or `FileNotFoundError`.

---

## 4. Environment Setup & System Dependencies

1. **Python 3.11:** Pinned repository-wide via `.python-version`. Ensure Python 3.11 is available on your system `PATH`.
2. **FFmpeg:** Required for audio extraction, duration-fitting, and remuxing:
   - **Windows:** `winget install Gyan.FFmpeg`
   - **macOS:** `brew install ffmpeg`
   - **Ubuntu/Debian:** `sudo apt update && sudo apt install -y ffmpeg`
3. **Deep Learning Tools (Stage 6):** PyTorch 2.0+ and Hugging Face Transformers (`pip install -r requirements.txt` inside `6. Sectence Construction/`).

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

---

<p align="center">
  <a href="README.md">🏠 Suite Overview</a> &bull; <a href="ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Instructions Manual</b></sub>
</p>
