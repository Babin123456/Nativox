# Nativox Manual & Operational Guide

Complete Architecture, Working Principles, and Module-by-Module Guide.

<!-- markdownlint-disable MD033 -->

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Suite_Readme-📖_README.md-009688?style=for-the-badge&logo=readme&logoColor=white" alt="Suite Readme" /></a>
  <a href="ARCHITECTURE.md"><img src="https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-3E8FC4?style=for-the-badge&logo=blueprint&logoColor=white" alt="Architecture" /></a>
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white" alt="Roadmap" /></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="MIT License" /></a>
</p>

---

## 📑 Table of Contents

1. [Suite Overview & Modular Philosophy](#1-suite-overview--modular-philosophy)
2. [Module-by-Module Instructions](#2-module-by-module-instructions)
   - [Module 1: MP4 to MP3 Extraction (`01_MP4_to_MP3/`)](#module-1-mp4-to-mp3-extraction)
   - [Module 2: MP3 to Text Transcription (`02_MP3_to_Text/`)](#module-2-mp3-to-text-transcription)
   - [Module 3: Text to Keyword Extraction (`03_Text_to_Keyword/`)](#module-3-text-to-keyword-extraction)
   - [Module 4: Keyword to Sentence Construction (`04_Keyword_to_Sentence_Construction/`)](#module-4-keyword-to-sentence-construction)
   - [Module 5(a): Keyword Translation Engine (`05a_Keyword_Translation__Sagnik/`)](#module-5a-keyword-translation-engine)
   - [Module 5(b): Sentence Reformation & Précis (`05b_Sentence_Reformation__Atanu/`)](#module-5b-sentence-reformation--precis)
   - [Module 6: Text → MP3 Speech Synthesis (`06_Converted_Text_to_MP3/`)](#module-6-text-to-mp3)
3. [Running the Modular Suite](#3-running-the-modular-suite)
4. [Environment Setup & System Dependencies](#4-environment-setup--system-dependencies)

---

## 1. Suite Overview & Modular Philosophy

The **Nativox** suite divides video dubbing and cross-lingual audio transformation into clearly isolated research and operational modules. Each directory represents a self-contained microservice or deep-learning module equipped with:

- An independent backend API (FastAPI) or standalone training/inference engine
- A dedicated interactive frontend (Stages 1 through 3, 5(a), 5(b)) or CLI/trainer suite (Stage 4)
- Independent virtual environment setup and execution procedures for Windows, macOS, and Linux
- A stage-specific `README.md` explaining operational principles and API contracts
- A pinned **Python 3.11** environment specification via the repository-wide `.python-version` file

This structure allows researchers and evaluators to inspect, benchmark, and run every stage independently without coupling issues.

---

## 2. Module-by-Module Instructions

### <a id="module-1-mp4-to-mp3-extraction"></a>Module 1: MP4 to MP3 Extraction (`01_MP4_to_MP3/`)

- **Core Function:** Ingests video files (`.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`) and extracts a clean, high-bitrate MP3 audio stream.
- **Working Principle:**
  - Invokes FFmpeg asynchronously: `ffmpeg -i input.mp4 -vn -acodec libmp3lame -q:a 2 output.mp3`.
  - Discards video frames cleanly to minimize disk and memory footprint.
  - Serves a synchronized side-by-side video and audio preview in the browser.
- **Execution:**

  ```bash
  cd 01_MP4_to_MP3/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8000
  ```

- **Port:** `http://127.0.0.1:8000`

---

### <a id="module-2-mp3-to-text-transcription"></a>Module 2: MP3 to Text Transcription (`02_MP3_to_Text/`)

- **Core Function:** Transcribes speech into timestamped text segments with high precision and acoustic speaker feature extraction.
- **Working Principle:**
  - Uses `faster-whisper` (CTranslate2 build of OpenAI Whisper) with Silero VAD.
  - Generates millisecond-accurate start and end timestamps per sentence.
  - Automatically identifies language and renders Indic scripts (Devanagari for Hindi, Bangla script for Bengali).
- **Execution:**

  ```bash
  cd 02_MP3_to_Text/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8001
  ```

- **Port:** `http://127.0.0.1:8001`

---

### <a id="module-3-text-to-keyword-extraction"></a>Module 3: Text to Keyword Extraction (`03_Text_to_Keyword/`)

- **Core Function:** Identifies salient keywords, key phrases, and technical terminology from the transcribed text.
- **Working Principle:**
  - Leverages multilingual **RAKE (Rapid Automatic Keyword Extraction)** with joint English, Hindi, and Bengali stopword elimination.
  - Scores words using co-occurrence frequency ($W_{\text{deg}} / W_{\text{freq}}$).
  - Classifies Unicode blocks (Latin, Devanagari, Bengali) for visual script proportion metering.
- **Execution:**

  ```bash
  cd 03_Text_to_Keyword/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8010
  ```

- **Port:** `http://127.0.0.1:8010`

---

### <a id="module-4-keyword-to-sentence-construction"></a>Module 4: Keyword to Sentence Construction (`04_Keyword_to_Sentence_Construction/`)

- **Core Function:** Learns canonical sentence syntax directly from PDF or Word documents and reconstructs broken/disordered sentences into fluent English.
- **Working Principle:**
  - Extracts clean reference sentences from `.pdf` or `.docx` documents using `pypdf` and `python-docx`.
  - Self-supervises training via synthetic noise generation (word jumbling, function word dropping, inflection distortion).
  - Fine-tunes a Google Flan-T5 Seq2Seq Transformer model using PyTorch and Hugging Face Transformers.
  - Provides an inference engine (`construct.py`) supporting interactive CLI testing, single-sentence inference, and batch file processing.
- **Execution:**

  ```bash
  cd 04_Keyword_to_Sentence_Construction
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt

  # Train the Seq2Seq Transformer on PDF corpus
  python train.py

  # Interactive live CLI testing
  python construct.py
  ```

---

### <a id="module-5a-keyword-translation-engine"></a>Module 5(a): Keyword Translation Engine (`05a_Keyword_Translation__Sagnik/`)

- **Core Function:** Translates extracted keywords and domain entities and generates phonetic pronunciation transliterations.
- **Working Principle:**
  - Employs `deep-translator` with failover resilience for technical terminology preservation.
  - Synthesizes readable Latin phonetic transliterations using `indic-transliteration` (ITRANS / Harvard-Kyoto).
  - Employs lightweight Unicode script detection to identify source scripts instantly.
- **Execution:**

  ```bash
  cd 05a_Keyword_Translation__Sagnik/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8011
  ```

- **Port:** `http://127.0.0.1:8011`

---

### <a id="module-5b-sentence-reformation--precis"></a>Module 5(b): Sentence Reformation & Précis (`05b_Sentence_Reformation__Atanu/`)

- **Core Function:** Disfluency cleaning, syntax restoration into meaningful Hindi, and strict 35%–40% paragraph précis compression.
- **Working Principle:**
  - Strips verbal fillers (*um, uh, basically, you know*) and restructures broken keywords or ASR speech into grammatically complete SOV Hindi sentences.
  - Analyzes transcript paragraphs from MP3 audio and algorithmically extracts an information-dense précis fitting strictly within 35%–40% of original word length:
    $$\lfloor 0.35 \times W_{\text{orig}} \rfloor \le W_{\text{precis}} \le \lceil 0.40 \times W_{\text{orig}} \rceil$$
- **Execution:**

  ```bash
  cd 05b_Sentence_Reformation__Atanu/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8012
  ```

- **Port:** `http://127.0.0.1:8012`

---

### <a id="module-6-text-to-mp3"></a>Module 6: Text → MP3 Speech Synthesis (`06_Converted_Text_to_MP3/`)

- **Core Function:** Converts text (reformed Hindi text from Stage 5(b), Bengali, or English) into natural-sounding MP3 speech audio using Microsoft Edge Neural TTS voices.
- **Working Principle:**
  - Uses `edge-tts` to access Microsoft Edge Neural Voices — zero API keys, zero GPU required.
  - Automatically validates that input text is in Bengali, English, or Hindi, rejecting unsupported languages.
  - Supports multiple dedicated voices across all three languages with adjustable speech rate and pitch.
  - Produces standard MP3 files ready for downstream HLS multi-track packaging or direct playback.
- **Execution:**

  ```bash
  cd 06_Converted_Text_to_MP3/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8013
  ```

- **Port:** `http://127.0.0.1:8013`

---

## 3. Running the Modular Suite

To test all modules simultaneously, you can run each stage in a separate terminal:

| Terminal | Module | Windows Command | Git Bash / Linux Command | Local URL / Mode |
| :--- | :--- | :--- | :--- | :--- |
| **Terminal 1** | Stage 1 (MP4 to MP3) | `cd 01_MP4_to_MP3/backend && python -m uvicorn main:app --reload --port 8000` | `cd 01_MP4_to_MP3/backend && python -m uvicorn main:app --reload --port 8000` | `http://127.0.0.1:8000` |
| **Terminal 2** | Stage 2 (MP3 to Text) | `cd 02_MP3_to_Text/backend && python -m uvicorn main:app --reload --port 8001` | `cd 02_MP3_to_Text/backend && python -m uvicorn main:app --reload --port 8001` | `http://127.0.0.1:8001` |
| **Terminal 3** | Stage 3 (Text to Keyword) | `cd 03_Text_to_Keyword/backend && python -m uvicorn main:app --reload --port 8010` | `cd 03_Text_to_Keyword/backend && python -m uvicorn main:app --reload --port 8010` | `http://127.0.0.1:8010` |
| **Terminal 4** | Stage 4 (Sentence Construction) | `cd 04_Keyword_to_Sentence_Construction && python construct.py` | `cd 04_Keyword_to_Sentence_Construction && python3 construct.py` | Interactive CLI |
| **Terminal 5** | Stage 5(a) (Keyword Translate) | `cd 05a_Keyword_Translation__Sagnik/backend && python -m uvicorn main:app --reload --port 8011` | `cd 05a_Keyword_Translation__Sagnik/backend && python -m uvicorn main:app --reload --port 8011` | `http://127.0.0.1:8011` |
| **Terminal 6** | Stage 5(b) (Sentence Reformation) | `cd 05b_Sentence_Reformation__Atanu/backend && python -m uvicorn main:app --reload --port 8012` | `cd 05b_Sentence_Reformation__Atanu/backend && python -m uvicorn main:app --reload --port 8012` | `http://127.0.0.1:8012` |
| **Terminal 7** | Stage 6 (Hindi Text → MP3) | `cd 06_Converted_Text_to_MP3/backend && python -m uvicorn main:app --reload --port 8013` | `cd 06_Converted_Text_to_MP3/backend && python -m uvicorn main:app --reload --port 8013` | `http://127.0.0.1:8013` |

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
3. **Deep Learning Tools (Stage 4):** PyTorch 2.0+ and Hugging Face Transformers (`pip install -r requirements.txt` inside `04_Keyword_to_Sentence_Construction/`).

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

---

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="README.md">🏠 Suite Overview</a> &bull; <a href="ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Instructions Manual</b></sub>
</p>
<!-- markdownlint-enable MD033 -->
