<!-- markdownlint-disable MD033 MD041 -->

<div align="center">

![Nativox Header](https://capsule-render.vercel.app/api?type=waving&color=0:4E65FF,50:92EFFD,100:3E8FC4&height=220&section=header&text=NATIVOX&fontSize=60&fontColor=FFFFFF&fontAlignY=38&desc=Modular%20Real-Time%20AI%20Multilingual%20Dubbing%20Suite&descFontSize=20&descColor=FFFFFF&descAlignY=62&animation=fadeIn)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
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

Each standalone stage can run completely independently as a self-contained microservice (with its own FastAPI backend, static favicon, and interactive OpenAPI documentation at `/docs`), while also chaining together into the master pipeline.

---

## 🗂️ Suite Structure & Modular Stages

| Stage Directory | Module Name | Documentation & Guide | Core Technology | Description |
| :--- | :--- | :--- | :--- | :--- |
| [`00_Auto_Pip/`](00_Auto_Pip) | **Automatic Master Dubbing Suite & UI** | [📖 Stage 0 Guide](00_Auto_Pip/README.md) | FastAPI / Orchestrator | Web dashboard on port 8000 uniting all 8 microservices; features acoustic speaker voice gender matching, dynamic pacing, and zero-truncation remuxing. |
| [`01_MP4_to_MP3/`](01_MP4_to_MP3) | **Audio Extractor & Stem Separator** | [📖 Stage 1 Guide](01_MP4_to_MP3/README.md) | FFmpeg (libmp3lame) | Ingests video (`.mp4`, `.mov`, `.mkv`), isolates audio tracks, and renders side-by-side synchronized preview. |
| [`02_MP3_to_Text/`](02_MP3_to_Text) | **Speech-To-Text (ASR) Engine** | [📖 Stage 2 Guide](02_MP3_to_Text/README.md) | faster-whisper / Silero VAD | Generates timestamped word-level and sentence-level transcripts with automatic language classification. |
| [`03_Text_to_Keyword/`](03_Text_to_Keyword) | **Salient Keyword Extractor** | [📖 Stage 3 Guide](03_Text_to_Keyword/README.md) | Multilingual RAKE / Script Tagger | Extracts domain-critical terminology, named entities, and technical keywords from spoken dialogue. |
| [`04_Keyword_to_Sentence_Construction/`](04_Keyword_to_Sentence_Construction) | **Sentence Construction & Syntax Restoration** | [📖 Stage 4 Guide](04_Keyword_to_Sentence_Construction/README.md) | Flan-T5 / Seq2Seq / PyTorch | Learns canonical syntax from PDF/DOCX documents to reconstruct fragmented/destructive sentences into fluent English. |
| [`05a_Keyword_Translation__Sagnik/`](05a_Keyword_Translation__Sagnik) | **Contextual Terminology Translation** | [📖 Stage 5(a) Guide](05a_Keyword_Translation__Sagnik/README.md) | deep-translator / indic-transliteration | Accurately translates technical vocabulary and synthesizes Romanized phonetic pronunciation guides. |
| [`05b_Sentence_Reformation__Atanu/`](05b_Sentence_Reformation__Atanu) | **Sentence Reformation & Précis** | [📖 Stage 5(b) Guide](05b_Sentence_Reformation__Atanu/README.md) | Disfluency Cleaner / Précis Budgeting | Reconstructs broken speech into meaningful Hindi and compresses full MP3 paragraphs to 35%–40% précis. |
| [`06_Converted_Text_to_MP3/`](06_Converted_Text_to_MP3) | **Hindi Text → MP3 Speech Synthesis** | [📖 Stage 6 Guide](06_Converted_Text_to_MP3/README.md) | Edge-TTS Neural Voices | Synthesizes reformed Hindi text into natural-sounding MP3 speech with multi-voice, rate, and pitch control. |
| [`07_Merge_MP3_with_MP4/`](07_Merge_MP3_with_MP4) | **Final Dubbed Video Assembly** | [📖 Stage 7 Guide](07_Merge_MP3_with_MP4/README.md) | FFmpeg Copy-Mode Remux | Merges the original source video with dubbed target-language audio, replacing English audio completely to produce the final dubbed MP4. |

---

## 🚀 Setup & Execution Guide

Each module in Nativox is an independent service. Choose **one** of the two setup tracks below based on your preference:

- **Track 1: Standard Python Setup** — Use if your system `python` is Python 3.11 (`winget install Python.Python.3.11`).
- **Track 2: Fast Setup via `uv` (Recommended)** — Automatically uses the pinned `.python-version` (3.11) with zero manual PATH configuration.

> [!IMPORTANT]
> **Must Use Python 3.11 (Avoid Python 3.14+):**
> Python 3.14 is a pre-release version lacking pre-compiled C/Rust binary wheels for `pydantic-core`, `faster-whisper`, `ctranslate2`, `av`, and `torch`.
> In PowerShell, always activate via `.\venv\Scripts\Activate.ps1`. Do **not** type `.\venv` alone (it is a directory).

---

### 📋 Universal Setup Cheatsheet (Copy & Paste by Shell)

#### Track 1 — Standard Python (Requires Python 3.11)

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows Git Bash:**

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

#### Track 2 — Fast Setup with `uv` (Recommended)

**Windows PowerShell:**

```powershell
uv venv --seed venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows Git Bash:**

```bash
uv venv --seed venv
source venv/Scripts/activate
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
uv venv --seed venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### ⚡ Running the Complete Pipeline
 
For the full end-to-end MP4-to-dubbed-MP4 workflow, use [`00_Auto_Pip/`](00_Auto_Pip). It provides both an **interactive Web UI** and a headless CLI orchestrator:

#### Option A: Interactive Web UI (Port 8000)

```bash
cd 00_Auto_Pip
python main.py
```
*(Or `uvicorn main:app --reload --port 8000`)*

Open your browser to:
👉 **`http://127.0.0.1:8000`**

Features:
- **Acoustic Speaker Voice Gender Matching:** Analyzes input speaker fundamental pitch ($F_0$ Hz) and automatically selects a matching male (`hi-IN-MadhurNeural`) or female (`hi-IN-SwaraNeural`) neural voice.
- **Zero Truncation Remuxing:** Preserves 100% of the original video duration without cutting video frames.
- **Side-by-Side Video Player:** Compare original video with dubbed output in real time.
- **Live Multi-Stage Stepper & Logs:** View status badges for all microservices (`8001`–`8014`) and real-time execution logs.

#### Option B: Headless Command-Line Runner

```bash
cd 00_Auto_Pip
python setup_env.py
python orchestrator.py "path/to/video.mp4"
```

Results are written to `00_Auto_Pip/jobs/job1` by default. Pass `--work-dir` to choose another output directory:

```bash
python orchestrator.py "path/to/video.mp4" --work-dir "path/to/output"
```

To check service health across all microservices:

```bash
python orchestrator.py --status
```

See the [automatic pipeline guide](00_Auto_Pip/README.md) for full service management, output files, ports, and troubleshooting.

---

### 🏃 Running Individual Stages

Select your preferred shell block below, copy it with one click, and paste it directly into your terminal.

#### Stage 1: Audio Extractor & Stem Separator (`01_MP4_to_MP3`)

*Port:* `http://127.0.0.1:8001` &bull; *Documentation:* [Stage 1 Guide](01_MP4_to_MP3/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 01_MP4_to_MP3
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8001
  ```

- **Windows Git Bash:**

  ```bash
  cd 01_MP4_to_MP3
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8001
  ```

- **macOS / Linux:**

  ```bash
  cd 01_MP4_to_MP3
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8001
  ```

---

#### Stage 2: Speech-To-Text (ASR) Engine (`02_MP3_to_Text`)

*Port:* `http://127.0.0.1:8002` &bull; *Documentation:* [Stage 2 Guide](02_MP3_to_Text/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 02_MP3_to_Text
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8002
  ```

- **Windows Git Bash:**

  ```bash
  cd 02_MP3_to_Text
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8002
  ```

- **macOS / Linux:**

  ```bash
  cd 02_MP3_to_Text
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8002
  ```

---

#### Stage 3: Salient Keyword Extractor (`03_Text_to_Keyword`)

*Port:* `http://127.0.0.1:8003` &bull; *Documentation:* [Stage 3 Guide](03_Text_to_Keyword/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 03_Text_to_Keyword
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8003
  ```

- **Windows Git Bash:**

  ```bash
  cd 03_Text_to_Keyword
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8003
  ```

- **macOS / Linux:**

  ```bash
  cd 03_Text_to_Keyword
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8003
  ```

---

#### Stage 4: Sentence Construction & Syntax Restoration (`04_Keyword_to_Sentence_Construction`)

*Port:* `http://127.0.0.1:8004` (FastAPI Microservice / Interactive Docs at `/docs`) &bull; *Documentation:* [Stage 4 Guide](04_Keyword_to_Sentence_Construction/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 04_Keyword_to_Sentence_Construction
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8004
  ```

- **Windows Git Bash:**

  ```bash
  cd 04_Keyword_to_Sentence_Construction
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8004
  ```

- **macOS / Linux:**

  ```bash
  cd 04_Keyword_to_Sentence_Construction
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8004
  ```

*(Interactive CLI: `cd 04_Keyword_to_Sentence_Construction && python construct.py`)*

---

#### Stage 5(a): Contextual Terminology Translation (`05a_Keyword_Translation__Sagnik`)

*Port:* `http://127.0.0.1:8011` &bull; *Documentation:* [Stage 5(a) Guide](05a_Keyword_Translation__Sagnik/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 05a_Keyword_Translation__Sagnik
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8011
  ```

- **Windows Git Bash:**

  ```bash
  cd 05a_Keyword_Translation__Sagnik
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8011
  ```

- **macOS / Linux:**

  ```bash
  cd 05a_Keyword_Translation__Sagnik
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8011
  ```

---

#### Stage 5(b): Sentence Reformation & Précis (`05b_Sentence_Reformation__Atanu`)

*Port:* `http://127.0.0.1:8012` &bull; *Documentation:* [Stage 5(b) Guide](05b_Sentence_Reformation__Atanu/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 05b_Sentence_Reformation__Atanu
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8012
  ```

- **Windows Git Bash:**

  ```bash
  cd 05b_Sentence_Reformation__Atanu
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8012
  ```

- **macOS / Linux:**

  ```bash
  cd 05b_Sentence_Reformation__Atanu
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8012
  ```

---

#### Stage 6: Hindi Text → MP3 Speech Synthesis (`06_Converted_Text_to_MP3`)

*Port:* `http://127.0.0.1:8013` &bull; *Documentation:* [Stage 6 Guide](06_Converted_Text_to_MP3/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 06_Converted_Text_to_MP3
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8013
  ```

- **Windows Git Bash:**

  ```bash
  cd 06_Converted_Text_to_MP3
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8013
  ```

- **macOS / Linux:**

  ```bash
  cd 06_Converted_Text_to_MP3
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8013
  ```

---

#### Stage 7: Final Dubbed Video Assembly (`07_Merge_MP3_with_MP4`)

*Port:* `http://127.0.0.1:8014` &bull; *Documentation:* [Stage 7 Guide](07_Merge_MP3_with_MP4/README.md)

- **Windows PowerShell:**

  ```powershell
  cd 07_Merge_MP3_with_MP4
  uv venv --seed venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8014
  ```

- **Windows Git Bash:**

  ```bash
  cd 07_Merge_MP3_with_MP4
  uv venv --seed venv
  source venv/Scripts/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8014
  ```

- **macOS / Linux:**

  ```bash
  cd 07_Merge_MP3_with_MP4
  uv venv --seed venv
  source venv/bin/activate
  pip install -r requirements.txt
  python -m uvicorn main:app --reload --port 8014
  ```

*(Note: If using standard Python 3.11 instead of `uv`, simply replace `uv venv --seed venv` with `python -m venv venv` or `python3 -m venv venv`)*

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
