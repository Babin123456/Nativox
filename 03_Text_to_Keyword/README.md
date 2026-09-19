# Stage 3: Salient Keyword Extractor

## Multilingual RAKE & Cross-Script Salient Terminology Engine

Part of the **Nativox** AI Multilingual Dubbing Suite.

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 2](https://img.shields.io/badge/Prev_Stage-Stage_2:_ASR-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../02_MP3_to_Text/README.md)
[![Stage 4](https://img.shields.io/badge/Next_Stage-Stage_4:_Construction-FF6B6B?style=for-the-badge&logo=pytorch&logoColor=white)](../04_Keyword_to_Sentence_Construction/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## 📖 Operational Overview

Stage 3 extracts salient, content-bearing domain terminology and named entities from transcripts generated in **Stage 2**. It supports text in **English**, **Hindi (Devanagari)**, **Bengali (Bangla script)**, and freely code-mixed speech without requiring heavy deep-learning model downloads.

The extracted keyword lexicon is transferred downstream to **Stage 4 (Keyword to Sentence Construction)** and **Stage 5 (Sentence Reformation & Translation)** to guide keyword retention and sentence reconstruction.

---

## 🛠️ Tech Stack & Key Features

- **Backend:** FastAPI (Python 3.11)
- **Algorithm:** Multilingual **RAKE (Rapid Automatic Keyword Extraction)**
  - Joint English + Hindi + Bengali stopword elimination in a single pass.
  - Seamless handling of code-mixed spoken phrases (e.g., *"ei video te amra automated dubbing model use korchi"*).
  - Co-occurrence matrix scoring ($W_{\text{deg}} / W_{\text{freq}}$) on candidate multi-word and single-word units.
  - Unicode block classification (Latin, Devanagari, Bengali) for script tagging.
- **Frontend:** Interactive dashboard with script balance visualizer and ranked keyword pill view.

---

## 📋 Prerequisites & Requirements

- **Python:** **3.11** (Repository pinned via root `.python-version`)
- **Dependencies:** Lightweight pure-Python NLP routines (no GPU or model weight downloads required)

---

## 🚀 Setup & Execution

### 1. Navigate to Backend Directory

```bash
cd 03_Text_to_Keyword/backend
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
python -m uvicorn main:app --reload --port 8010
```

The web interface will open at **`http://127.0.0.1:8010`**.

> [!IMPORTANT]
> **Access via `http://127.0.0.1:8010`, not raw `index.html`:**
> The FastAPI backend serves `frontend/index.html` directly on port `8010`. Opening `index.html` directly via `file:///` causes browser CORS errors that block requests to `/api/keywords`.

---

## 🏛️ Pipeline Architecture

```mermaid
graph LR
    A["Raw Transcript from Stage 2"] --> B["Multi-Script Tokenizer"]
    B --> C["English / Hindi / Bengali Stopword Eliminator"]
    C --> D["RAKE Co-occurrence Matrix Calculator"]
    D --> E["Ranked Salient Keywords & Script Tags"]
    E -.-> F["Input to Stage 4 (Sentence Construction)"]

    linkStyle default stroke:#0284C7,stroke-width:2.5px;
```

---

## 🔌 API Reference

### `POST /api/keywords`

Extracts ranked multi-word and single-word keywords from input text.

- **Content-Type:** `application/json`
- **Request Body:**

  ```json
  {
    "text": "In this tutorial we will train a neural network for computer vision applications.",
    "max_keywords": 8
  }
  ```

- **Response Body:**

  ```json
  {
    "total_keywords": 4,
    "keywords": [
      { "keyword": "computer vision applications", "score": 9.0 },
      { "keyword": "neural network", "score": 4.0 },
      { "keyword": "tutorial", "score": 1.0 },
      { "keyword": "train", "score": 1.0 }
    ],
    "script_distribution": {
      "en": 1.0,
      "hi": 0.0,
      "bn": 0.0
    },
    "dominant_script": "en",
    "script_labels": {
      "en": "English",
      "hi": "Hindi",
      "bn": "Bengali",
      "mixed": "Mixed"
    }
  }
  ```

---

## 📁 Project Structure

```text
03_Text_to_Keyword/
├── README.md                  # Stage documentation
├── backend/
│   ├── main.py                # FastAPI endpoints and static file routing
│   ├── requirements.txt       # FastAPI, Uvicorn, Pydantic
│   └── app/
│       ├── keyword_extractor.py # Multilingual RAKE co-occurrence engine
│       ├── language_utils.py    # Unicode-script tagging (Latin/Devanagari/Bengali)
│       └── stopwords.py         # Curated English, Hindi, and Bengali stopword sets
└── frontend/
    └── index.html             # Interactive text input, script meter, and keyword cards
```

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

---

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="../README.md">🏠 Back to Suite Overview</a> &bull; <a href="../ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="../INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="../ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Module 3 Documentation</b></sub>
</p>
<!-- markdownlint-enable MD033 -->
