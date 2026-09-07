<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:4E65FF,50:92EFFD,100:3E8FC4&height=220&section=header&text=NATIVOX&fontSize=60&fontColor=FFFFFF&fontAlignY=38&desc=Modular%20Real-Time%20AI%20Multilingual%20Dubbing%20Suite&descFontSize=20&descColor=FFFFFF&descAlignY=62&animation=fadeIn" width="100%" alt="Nativox Header"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"/>
  <img src="https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Architecture-Stage--by--Stage%20Decoupled-FF6B6B?style=for-the-badge&logo=blueprint&logoColor=white" alt="Decoupled Architecture"/>
  <img src="https://img.shields.io/badge/License-MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="License MIT"/>
</p>

---

## 📖 Overview

**Nativox** is an AI-powered multilingual video dubbing and contextual voice translation system. To maintain maximum modularity, research extensibility, and clarity for academic review and production debugging, the system is organized into decoupled pipeline stages as well as unified end-to-end services.

Each standalone stage can run completely independently as a self-contained microservice (with its own frontend and backend), while also chaining together into the master pipeline.

---

## 🗂️ Suite Structure & Modular Stages

| Stage Directory | Module Name | Core Technology | Description |
| :--- | :--- | :--- | :--- |
| [`1. mp4 to mp3/`](file:///d:/Projects/AI-Powered-Multilingual-Real-Time-Dubbing-System/Nativox/1.%20mp4%20to%20mp3) | **Audio Extractor & Stem Separator** | FFmpeg / Demucs | Ingests video (`.mp4`, `.mov`, `.mkv`), isolates vocal tracks, and preserves background ambient audio. |
| [`2. mp3 to Text/`](file:///d:/Projects/AI-Powered-Multilingual-Real-Time-Dubbing-System/Nativox/2.%20mp3%20to%20Text) | **Speech-To-Text (ASR) Engine** | OpenAI Whisper / Faster-Whisper | Generates timestamped word-level and sentence-level transcripts with speaker pitch/gender detection. |
| [`3. Text to Keyword/`](file:///d:/Projects/AI-Powered-Multilingual-Real-Time-Dubbing-System/Nativox/3.%20Text%20to%20Keyword) | **Salient Keyword Extractor** | KeyBERT / spaCy / Rake-NLTK | Extracts domain-critical terminology, named entities, and technical keywords from spoken dialogue. |
| [`4. Keyword Translate/`](file:///d:/Projects/AI-Powered-Multilingual-Real-Time-Dubbing-System/Nativox/4.%20Keyword%20Translate) | **Contextual Terminology Translation** | Deep-Translator / MarianMT / LLMs | Accurately translates technical vocabulary into Indic & European languages without literal distortion. |
| **Pipeline Core** | **Sentence Reformation & Compression** | Local LLM / Semantic Budgeting | Contextual restructuring (SVO $\to$ SOV) and duration compression to fit strict millisecond video slots. |
| **Synthesis & Packaging** | **Neural TTS & HLS Delivery** | Edge-TTS / XTTS-v2 / HLS-DASH | Gender-matched voice synthesis and decoupled multi-audio track streaming without re-encoding video. |

---

## 🚀 Quick Execution Guide

Each module provides native one-click execution scripts for both Windows and Unix:

### Running Individual Stages:

* **Stage 1 (MP4 $\rightarrow$ MP3):**
  ```bash
  cd "1. mp4 to mp3"
  # Windows
  run.bat
  # Linux/macOS
  ./run.sh
  ```
  *Accessible at `http://127.0.0.1:8000`*

* **Stage 2 (MP3 $\rightarrow$ Text):**
  ```bash
  cd "2. mp3 to Text/backend"
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8001
  ```

* **Stage 3 (Text $\rightarrow$ Keyword):**
  ```bash
  cd "3. Text to Keyword"
  run.bat
  ```
  *Accessible at `http://127.0.0.1:8002`*

* **Stage 4 (Keyword Translate):**
  ```bash
  cd "4. Keyword Translate"
  run.bat
  ```
  *Accessible at `http://127.0.0.1:8003`*

---

## 📑 Core Documentation

For detailed technical designs, architectural blueprints, and stage references:
- **[Architecture Deep-Dive](ARCHITECTURE.md):** Complete end-to-end dataflow, state machines, and microservice layout.
- **[Future Roadmap & Directives](ROADMAP.md):** Faculty directives, LLM duration compression, and YouTube-style HLS multi-audio track sync.
- **[Setup & Deployment Guide](INSTRUCTIONS.md):** Environment configuration, GPU acceleration, and package installation.
