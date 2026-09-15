# Stage 3: Salient Keyword Extractor

## Multilingual RAKE & Cross-Script Salient Terminology Engine

Part of the **Nativox** AI Multilingual Dubbing Suite.

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 2](https://img.shields.io/badge/Prev_Stage-Stage_2:_ASR-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../2.%20mp3%20to%20Text/README.md)
[![Stage 4](https://img.shields.io/badge/Next_Stage-Stage_4:_Translate-FF6B6B?style=for-the-badge&logo=fastapi&logoColor=white)](../4.%20Keyword%20Translate/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## 📖 Operational Overview

Stage 3 extracts salient, content-bearing domain terminology and named entities from transcripts generated in **Stage 2**. It supports text in **English**, **Hindi (Devanagari)**, **Bengali (Bangla script)**, and freely code-mixed speech without requiring heavy deep-learning model downloads.

The extracted keyword lexicon is transferred to **Stage 4 (Keyword Translation)** for technical terminology mapping and to **Stage 5 (Sentence Reformation)** to guide keyword retention budgets.

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
cd "3. Text to Keyword/backend"
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

The web interface will be available at: **`http://127.0.0.1:8010`**

> [!IMPORTANT]
> **Access via `http://127.0.0.1:8010`, not raw `index.html`:**
> The FastAPI backend serves `frontend/index.html` directly on port `8010`. Opening `index.html` as a local `file:///` path causes browser CORS errors that block requests to `/api/extract-keywords`.

---

## 🏛️ Pipeline Architecture

```mermaid
graph LR
    A["Input Transcript Text"] --> B["Multilingual Stopword Filter (En/Hi/Bn)"]
    B --> C["Co-occurrence Matrix Scoring (RAKE)"]
    D["Script Block Tagger"]
    B --> D
    C --> E["Ranked Salient Keywords"]
    D --> E
    E -.-> F["Input to Stage 4 & Stage 5"]

    linkStyle default stroke:#0284C7,stroke-width:2.5px;
```

---

## 🔌 API Reference

### `POST /api/extract-keywords`

Extracts and ranks salient keywords from multilingual or code-mixed input.

- **Content-Type:** `application/json`
- **Request Body:**

  ```json
  {
    "text": "Artificial intelligence and machine learning are transforming multilingual dubbing in Kolkata and Delhi.",
    "top_n": 10
  }
  ```

- **Response Body:**

  ```json
  {
    "keywords": [
      {
        "word": "intelligence",
        "score": 4.0,
        "relative_score": 100.0,
        "language": "en"
      },
      {
        "word": "dubbing",
        "score": 3.5,
        "relative_score": 87.5,
        "language": "en"
      }
    ],
    "language_labels": {
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
3. Text to Keyword/
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

<p align="center">
  <a href="../README.md">🏠 Back to Suite Overview</a> &bull; <a href="../ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="../INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="../ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Module 3 Documentation</b></sub>
</p>
