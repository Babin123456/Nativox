<div align="center">

![Nativox Header](https://capsule-render.vercel.app/api?type=waving&color=0:4E65FF,50:92EFFD,100:3E8FC4&height=220&section=header&text=NATIVOX&fontSize=60&fontColor=FFFFFF&fontAlignY=38&desc=Modular%20Real-Time%20AI%20Multilingual%20Dubbing%20Suite&descFontSize=20&descColor=FFFFFF&descAlignY=62&animation=fadeIn)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Architecture-Stage--by--Stage%20Decoupled-FF6B6B?style=for-the-badge&logo=blueprint&logoColor=white" alt="Decoupled Architecture" />
</p>

<p align="center">
  <a href="ARCHITECTURE.md"><img src="https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-3E8FC4?style=for-the-badge&logo=blueprint&logoColor=white" alt="Architecture" /></a>
  <a href="INSTRUCTIONS.md"><img src="https://img.shields.io/badge/Instructions-📖_INSTRUCTIONS.md-4FAE7A?style=for-the-badge&logo=googledocs&logoColor=white" alt="Instructions" /></a>
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white" alt="Roadmap" /></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="License" /></a>
</p>

</div>

---

## 📖 Overview

**Nativox** is an AI-powered multilingual video dubbing and contextual voice translation system. To maintain maximum modularity, research extensibility, and clarity for academic review and production debugging, the system is organized into decoupled pipeline stages as well as unified end-to-end services.

Each standalone stage can run completely independently as a self-contained microservice (with its own frontend and backend), while also chaining together into the master pipeline.

---

## 🗂️ Suite Structure & Modular Stages

| Stage Directory | Module Name | Documentation & Guide | Core Technology | Description |
| :--- | :--- | :--- | :--- | :--- |
| [`1. mp4 to mp3/`](1.%20mp4%20to%20mp3) | **Audio Extractor & Stem Separator** | [📖 Stage 1 Guide](1.%20mp4%20to%20mp3/README.md) | FFmpeg / Demucs | Ingests video (`.mp4`, `.mov`, `.mkv`), isolates vocal tracks, and preserves background ambient audio. |
| [`2. mp3 to Text/`](2.%20mp3%20to%20Text) | **Speech-To-Text (ASR) Engine** | [📖 Stage 2 Guide](2.%20mp3%20to%20Text/README.md) | OpenAI Whisper / Faster-Whisper | Generates timestamped word-level and sentence-level transcripts with speaker pitch/gender detection. |
| [`3. Text to Keyword/`](3.%20Text%20to%20Keyword) | **Salient Keyword Extractor** | [📖 Stage 3 Guide](3.%20Text%20to%20Keyword/README.md) | KeyBERT / spaCy / Rake-NLTK | Extracts domain-critical terminology, named entities, and technical keywords from spoken dialogue. |
| [`4. Keyword Translate/`](4.%20Keyword%20Translate) | **Contextual Terminology Translation** | [📖 Stage 4 Guide](4.%20Keyword%20Translate/README.md) | Deep-Translator / MarianMT / LLMs | Accurately translates technical vocabulary into Indic & European languages without literal distortion. |
| [`5. Sentence Reformation/`](5.%20Sentence%20Reformation) | **Sentence Reformation & Précis** | [📖 Stage 5 Guide](5.%20Sentence%20Reformation/README.md) | Disfluency Cleaner / Précis Budgeting | Reconstructs broken speech into meaningful Hindi and compresses full MP3 paragraphs to 35%–40% précis. |
| **Synthesis & Packaging** | **Neural TTS & HLS Delivery** | *Internal Service* | Edge-TTS / XTTS-v2 / HLS-DASH | Gender-matched voice synthesis and decoupled multi-audio track streaming without re-encoding video. |

---

## 🚀 Quick Execution Guide

Each module provides native one-click execution scripts (`run.bat` for Windows and `run.sh` for Git Bash / Linux / macOS). For detailed line-by-line setup, requirements, and manual venv commands, click into each stage's dedicated README:

### Running Individual Stages

- **Stage 1 (MP4 $\rightarrow$ MP3):** ➔ *[Read Stage 1 Manual & Line-by-Line Guide](1.%20mp4%20to%20mp3/README.md)*

  ```bash
  cd "1. mp4 to mp3"
  # Windows (CMD / PowerShell)
  .\run.bat
  # Git Bash / macOS / Linux
  ./run.sh
  ```

  *Accessible at `http://127.0.0.1:8000`*

- **Stage 2 (MP3 $\rightarrow$ Text):** ➔ *[Read Stage 2 Manual & Line-by-Line Guide](2.%20mp3%20to%20Text/README.md)*

  ```bash
  cd "2. mp3 to Text"
  # Windows (CMD / PowerShell)
  .\run.bat
  # Git Bash / macOS / Linux
  ./run.sh
  ```

  *Accessible at `http://127.0.0.1:8001`*

- **Stage 3 (Text $\rightarrow$ Keyword):** ➔ *[Read Stage 3 Manual & Line-by-Line Guide](3.%20Text%20to%20Keyword/README.md)*

  ```bash
  cd "3. Text to Keyword"
  # Windows (CMD / PowerShell)
  .\run.bat
  # Git Bash / macOS / Linux
  ./run.sh
  ```

  *Accessible at `http://127.0.0.1:8002`*

- **Stage 4 (Keyword Translate):** ➔ *[Read Stage 4 Manual & Line-by-Line Guide](4.%20Keyword%20Translate/README.md)*

  ```bash
  cd "4. Keyword Translate"
  # Windows (CMD / PowerShell)
  .\run.bat
  # Git Bash / macOS / Linux
  ./run.sh
  ```

  *Accessible at `http://127.0.0.1:8003`*

- **Stage 5 (Sentence Reformation & Précis):** ➔ *[Read Stage 5 Manual & Line-by-Line Guide](5.%20Sentence%20Reformation/README.md)*

  ```bash
  cd "5. Sentence Reformation"
  # Windows (CMD / PowerShell)
  .\run.bat
  # Git Bash / macOS / Linux
  ./run.sh
  ```

  *Accessible at `http://127.0.0.1:8012`*

---

## 📑 Core Documentation

For detailed technical designs, architectural blueprints, and stage references:

- **[Architecture Deep-Dive](ARCHITECTURE.md):** Complete end-to-end dataflow, state machines, and microservice layout.
- **[Future Roadmap & Directives](ROADMAP.md):** Faculty directives, LLM duration compression, and YouTube-style HLS multi-audio track sync.
- **[Setup & Deployment Guide](INSTRUCTIONS.md):** Environment configuration, GPU acceleration, and package installation.

---

## 👥 Project Team & Mentorship

<div align="center">

### 🎓 Final Year Major Project — B.Tech Computer Science & Engineering

<table align="center">
  <tr>
    <th align="center" width="60%"><b>👨‍💻 Student Contributors</b></th>
    <th align="center" width="40%"><b>👨‍🏫 Guided Under</b></th>
  </tr>
  <tr>
    <td align="center">
      <b>Atanu Saha</b><br/>
      <b>Babin Bid</b><br/>
      <b>Rohit Kr Adak</b><br/>
      <b>Sagnik Bachhar</b>
    </td>
    <td align="center">
      <b>Dr. Debjit Ghosh</b><br/>
      <i>Department of Computer Science & Engineering</i>
    </td>
  </tr>
</table>

</div>

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:E8A33D,50:FF6B6B,100:3E8FC4&height=120&section=footer&animation=fadeIn" width="100%" alt="Footer Wave" />
</p>

<p align="center">
  <sub>
    Made with ❤️ by <b>Atanu, Babin, Rohit & Sagnik</b> • Guided by <b>Dr. Debjit Ghosh</b><br/>
    <b>🎙️ Nativox</b> — Empowering Multilingual Communication
  </sub>
</p>
