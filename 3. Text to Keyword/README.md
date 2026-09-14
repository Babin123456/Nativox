# Text to Keyword Extractor

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 2](https://img.shields.io/badge/Prev_Stage-Stage_2:_ASR-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../2.%20mp3%20to%20Text/README.md)
[![Stage 4](https://img.shields.io/badge/Next_Stage-Stage_4:_Translate-FF6B6B?style=for-the-badge&logo=fastapi&logoColor=white)](../4.%20Keyword%20Translate/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)

---

A standalone microservice that extracts **salient single-word keywords** — filtering stopwords and non-content words — from text in **English**, **Hindi**, **Bengali**, and **freely code-mixed combinations of all three**. This is the standalone implementation of **Stage 3 (Keyword Extraction)** from the Nativox pipeline.

---

## 🛠️ Tech Stack & Working Principle

- **Backend:** FastAPI (Python)
- **Algorithm:** Multilingual **RAKE (Rapid Automatic Keyword Extraction)**
  - Applies a combined English + Hindi + Bengali stopword list in a single pass.
  - Handles code-mixed sentences (e.g. *"ei video ta te amra automated dubbing model use korchi"*) seamlessly without needing language segmentation.
  - Scores words based on word degree and co-occurrence frequency within candidate phrases.
  - Tags detected Unicode scripts (Latin, Devanagari, Bengali) for visual highlighting.
- **Frontend:** Single-page dashboard with real-time script-mix meter and ranked keyword pills.

---

## 📋 Requirements

- **Python:** 3.10 or 3.11 recommended
- **Dependencies:** Pure Python NLP algorithms (no heavy GPU model weights required).

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

Once running, navigate to: **`http://127.0.0.1:8002`** (or configured port `8010`)

> [!IMPORTANT]
> **Access via `http://127.0.0.1:8002`, not raw `index.html`:**
> The FastAPI backend serves `frontend/index.html` directly on the server port. Double-clicking `index.html` locally will open it under `file:///` and fail to connect to `/api/extract-keywords`. Do **not** delete `frontend/index.html`, as it is required by the backend to serve the frontend interface.

---

## ⚙️ Manual Setup

### Windows PowerShell

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8002
```

### Git Bash (Windows)

```bash
cd backend
py -3.11 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8002
```

### macOS / Linux

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8002
```

---

## 🔌 API Reference

### `POST /api/extract-keywords`

**Request:**

```json
{
  "text": "Artificial intelligence and machine learning are transforming multilingual dubbing in Kolkata and Delhi.",
  "top_n": 10
}
```

**Response:**

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
├── README.md
├── run.bat
├── run.sh
├── backend/
│   ├── main.py                  # FastAPI app + REST endpoints
│   ├── requirements.txt
│   └── app/
│       ├── keyword_extractor.py # Multilingual RAKE co-occurrence engine
│       ├── language_utils.py    # Unicode-script tagging (Latin/Devanagari/Bengali)
│       └── stopwords.py         # Curated English, Hindi, and Bengali stopword dictionaries
└── frontend/
    └── index.html               # Interactive input, script meter, and keyword cards
```
