<!-- markdownlint-disable MD033 MD041 -->

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
<!-- markdownlint-enable MD033 -->

---

## 📖 Overview

**Nativox** is an AI-powered multilingual video dubbing and contextual voice translation system. To maintain maximum modularity, research extensibility, and clarity for academic review and production debugging, the system is organized into decoupled pipeline stages as well as unified end-to-end services.

Each standalone stage can run completely independently as a self-contained microservice (with its own frontend and backend), while also chaining together into the master pipeline.

---

## 🗂️ Suite Structure & Modular Stages

| Stage Directory | Module Name | Documentation & Guide | Core Technology | Description |
| :--- | :--- | :--- | :--- | :--- |
| [`01_MP4_to_MP3/`](01_MP4_to_MP3) | **Audio Extractor & Stem Separator** | [📖 Stage 1 Guide](01_MP4_to_MP3/README.md) | FFmpeg (libmp3lame) | Ingests video (`.mp4`, `.mov`, `.mkv`), isolates audio tracks, and renders side-by-side synchronized preview. |
| [`02_MP3_to_Text/`](02_MP3_to_Text) | **Speech-To-Text (ASR) Engine** | [📖 Stage 2 Guide](02_MP3_to_Text/README.md) | faster-whisper / Silero VAD | Generates timestamped word-level and sentence-level transcripts with automatic language classification. |
| [`03_Text_to_Keyword/`](03_Text_to_Keyword) | **Salient Keyword Extractor** | [📖 Stage 3 Guide](03_Text_to_Keyword/README.md) | Multilingual RAKE / Script Tagger | Extracts domain-critical terminology, named entities, and technical keywords from spoken dialogue. |
| [`04_Keyword_to_Sentence_Construction/`](04_Keyword_to_Sentence_Construction) | **Sentence Construction & Syntax Restoration** | [📖 Stage 4 Guide](04_Keyword_to_Sentence_Construction/README.md) | Flan-T5 / Seq2Seq / PyTorch | Learns canonical syntax from PDF/DOCX documents to reconstruct fragmented/destructive sentences into fluent English. |
| [`05a_Keyword_Translation__Sagnik/`](05a_Keyword_Translation__Sagnik) | **Contextual Terminology Translation** | [📖 Stage 5(a) Guide](05a_Keyword_Translation__Sagnik/README.md) | deep-translator / indic-transliteration | Accurately translates technical vocabulary and synthesizes Romanized phonetic pronunciation guides. |
| [`05b_Sentence_Reformation__Atanu/`](05b_Sentence_Reformation__Atanu) | **Sentence Reformation & Précis** | [📖 Stage 5(b) Guide](05b_Sentence_Reformation__Atanu/README.md) | Disfluency Cleaner / Précis Budgeting | Reconstructs broken speech into meaningful Hindi and compresses full MP3 paragraphs to 35%–40% précis. |
| [`06_Converted_Text_to_MP3/`](06_Converted_Text_to_MP3) | **Hindi Text → MP3 Speech Synthesis** | [📖 Stage 6 Guide](06_Converted_Text_to_MP3/README.md) | Edge-TTS Neural Voices | Synthesizes reformed Hindi text into natural-sounding MP3 speech with multi-voice, rate, and pitch control. |

---

## 🚀 Setup & Execution Guide

Each module provides an independent service that can be set up and run manually using standard Python virtual environments. For detailed line-by-line setup, requirements, and API specifications, click into each stage's dedicated README:

### Running Individual Stages

- **Stage 1 (MP4 $\rightarrow$ MP3):** ➔ *[Read Stage 1 Manual & Line-by-Line Guide](01_MP4_to_MP3/README.md)*

  ```bash
  cd 01_MP4_to_MP3/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8000
  ```

  *Accessible at `http://127.0.0.1:8000`*

- **Stage 2 (MP3 $\rightarrow$ Text):** ➔ *[Read Stage 2 Manual & Line-by-Line Guide](02_MP3_to_Text/README.md)*

  ```bash
  cd 02_MP3_to_Text/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8001
  ```

  *Accessible at `http://127.0.0.1:8001`*

- **Stage 3 (Text $\rightarrow$ Keyword):** ➔ *[Read Stage 3 Manual & Line-by-Line Guide](03_Text_to_Keyword/README.md)*

  ```bash
  cd 03_Text_to_Keyword/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8010
  ```

  *Accessible at `http://127.0.0.1:8010`*

- **Stage 4 (Keyword to Sentence Construction):** ➔ *[Read Stage 4 Manual & Line-by-Line Guide](04_Keyword_to_Sentence_Construction/README.md)*

  ```bash
  cd 04_Keyword_to_Sentence_Construction
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python train.py      # Train Seq2Seq Transformer on PDF corpus
  python construct.py  # Interactive sentence reconstruction testing
  ```

- **Stage 5(a) (Keyword Translate):** ➔ *[Read Stage 5(a) Manual & Line-by-Line Guide](05a_Keyword_Translation__Sagnik/README.md)*

  ```bash
  cd 05a_Keyword_Translation__Sagnik/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8011
  ```

  *Accessible at `http://127.0.0.1:8011`*

- **Stage 5(b) (Sentence Reformation & Précis):** ➔ *[Read Stage 5(b) Manual & Line-by-Line Guide](05b_Sentence_Reformation__Atanu/README.md)*

  ```bash
  cd 05b_Sentence_Reformation__Atanu/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8012
  ```

  *Accessible at `http://127.0.0.1:8012`*

- **Stage 6 (Hindi Text → MP3):** ➔ *[Read Stage 6 Manual & Line-by-Line Guide](06_Converted_Text_to_MP3/README.md)*

  ```bash
  cd 06_Converted_Text_to_MP3/backend
  python -m venv venv
  # Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8013
  ```

  *Accessible at `http://127.0.0.1:8013`*

---

## 📑 Core Documentation

For detailed technical designs, architectural blueprints, and stage references:

- **[Architecture Deep-Dive](ARCHITECTURE.md):** Complete end-to-end dataflow, state machines, and microservice layout.
- **[Future Roadmap & Directives](ROADMAP.md):** Faculty directives, LLM duration compression, and YouTube-style HLS multi-audio track sync.
- **[Setup & Deployment Guide](INSTRUCTIONS.md):** Environment configuration, GPU acceleration, and package installation.

---

## 👥 Project Team & Mentorship

<!-- markdownlint-disable MD033 -->
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
  <a href="README.md">🏠 Suite Overview</a> &bull; <a href="ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub>
    Made with ❤️ by <b>Atanu, Babin, Rohit & Sagnik</b> • Guided by <b>Dr. Debjit Ghosh</b><br/>
    <b>🎙️ Nativox</b> — Empowering Multilingual Communication &bull; <b>End of Suite Documentation</b>
  </sub>
</p>
<!-- markdownlint-enable MD033 -->
