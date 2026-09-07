# Keyword Translation Stage

[![Suite Readme](https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Stage 3](https://img.shields.io/badge/Prev_Stage-Stage_3:_Keyword-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white)](../3.%20Text%20to%20Keyword/README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)

---

A standalone microservice that translates a **batch of keywords or domain terminology** — in any combination of **English**, **Hindi**, and **Bengali** — into a single target language while preserving technical meaning and order. This is the standalone implementation of **Stage 4 (Keyword Translation)** from the Nativox pipeline.

---

## 🛠️ Tech Stack & Working Principle

- **Backend:** FastAPI (Python) + `deep-translator` + `indic-transliteration`
- **Frontend:** Single-page reactive UI with Romanized pronunciation guides.
- **Workflow:**
  1. **Unicode Detection:** Automatically identifies input script (Devanagari $\rightarrow$ Hindi, Bengali script $\rightarrow$ Bengali, Latin $\rightarrow$ English) without running expensive language models.
  2. **Batch Translation:** Translates terms into the selected target language via translation endpoints with built-in resilient fallback.
  3. **Phonetic Pronunciation Guide:** Generates readable Latin transliterations for Hindi and Bengali terms (e.g. *पानी* $\rightarrow$ `pani`, *জল* $\rightarrow$ `jala`).

---

## 📋 Requirements

- **Python:** **3.10 or 3.11** (Recommended: avoids pre-release compatibility issues)
- **Internet Access:** Required for translation endpoints.

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

Once running, navigate to: **`http://127.0.0.1:8003`** (or configured port `8011`)

---

## ⚙️ Manual Setup

### Windows PowerShell

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8003
```

### Git Bash (Windows)

```bash
cd backend
py -3.11 -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8003
```

### macOS / Linux

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn main:app --reload --port 8003
```

---

## 🔌 API Reference

### `POST /api/translate-batch`

**Request:**

```json
{
  "keywords": ["water", "पानी", "আকাশ", "computer"],
  "target_language": "hindi"
}
```

**Response:**

```json
{
  "target_language": "hindi",
  "target_label": "Hindi",
  "results": [
    {
      "original": "water",
      "detected_language": "english",
      "detected_label": "English",
      "translated_text": "पानी",
      "target_language": "hindi",
      "target_label": "Hindi",
      "pronunciation": "pani"
    },
    {
      "original": "computer",
      "detected_language": "english",
      "detected_label": "English",
      "translated_text": "कंप्यूटर",
      "target_language": "hindi",
      "target_label": "Hindi",
      "pronunciation": "kampyutara"
    }
  ]
}
```

---

## 📁 Project Structure

```text
4. Keyword Translate/
├── README.md
├── run.bat
├── run.sh
├── backend/
│   ├── main.py                  # FastAPI app + translation endpoints
│   ├── requirements.txt         # deep-translator, indic-transliteration, fastapi
│   └── app/
│       ├── translate_service.py # Batch translation logic & error fallback
│       └── detect.py            # Fast Unicode block script detection
└── frontend/
    └── index.html               # Batch keyword translation UI with phonetic badges
```
