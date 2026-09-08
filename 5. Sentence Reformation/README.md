# Stage 5: Sentence Reformation & Précis Compression

**English $\to$ Hindi Meaningful Sentence Reformation & 35%–40% Duration Budgeting Engine**

Part of the **Nativox** AI Multilingual Dubbing Suite.

[![Suite Readme](https://img.shields.io/badge/Suite_Readme-📖_README.md-009688?style=for-the-badge&logo=readme&logoColor=white)](../README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-3E8FC4?style=for-the-badge&logo=blueprint&logoColor=white)](../ARCHITECTURE.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white)](../ROADMAP.md)

---

## 📖 Operational Overview

Stage 5 addresses two critical directives set by project mentor **Dr. Debjit Ghosh**:

1. **Task 1: Meaningless $\to$ Meaningful Sentence Reformation:**  
   Spoken audio transcripts and raw translated keyword sequences often lack grammatical coherence, case markers (*vibhakti*), and correct word order. Stage 5 takes meaningless or broken speech segments as input, eliminates verbal disfluencies (*"um, uh, basically, you know"*), restores predicate syntax, and synthesizes natural, grammatically correct Hindi sentences (Subject-Object-Verb, SOV).

2. **Task 2: 35%–40% Précis Paragraph Compression:**  
   Spoken translation from English into Indic languages naturally inflates duration and syllable count. If dubbed audio is not compressed, it overflows the video time window. Stage 5 takes the full transcribed paragraph from the MP3 audio file and compresses it into an information-dense précis strictly within **35%–40%** of the original word count in Hindi while preserving 100% of the core meaning and technical facts.

---

## 📐 Mathematical Formulation

### 1. Précis Word Budget Window
For a source transcript paragraph with $W_{\text{orig}}$ words:
$$\lfloor 0.35 \times W_{\text{orig}} \rfloor \le W_{\text{precis}} \le \lceil 0.40 \times W_{\text{orig}} \rceil$$

### 2. Sentence & Clause Salience Scoring
Each candidate clause $c$ within sentence $s$ is ranked according to its keyword density and structural position:
$$\text{Score}(c) = \left( 2 \cdot \frac{\text{Hits}(c, \mathcal{K})}{\text{Length}(c)} + \text{PosWeight}(s) \right) \times \text{Penalty}(s)$$

Where:
- $\mathcal{K}$ is the set of prominent non-stopword technical keywords.
- $\text{PosWeight}(s) = 1.2$ for opening and thesis-concluding statements.
- $\text{Penalty}(s) = 0.8$ for excessively long spoken run-on clauses.

---

## ⚡ Quick Start

### Running the Service

```bash
cd "5. Sentence Reformation"

# Linux / macOS / Git Bash
./run.sh

# Windows (CMD / PowerShell)
.\run.bat
```

The web interface will open at **`http://127.0.0.1:8012`**.

---

## 🔌 API Specification

### 1. Reconstruct Broken Sentence
- **Endpoint:** `POST /api/reconstruct`
- **Request Body:**
  ```json
  {
    "text": "uh video we basically train neural network computer vision model you know",
    "target_language": "hindi"
  }
  ```
- **Response Body:**
  ```json
  {
    "original_text": "uh video we basically train neural network computer vision model you know",
    "cleaned_english": "In this video, we train neural network computer vision model.",
    "meaningful_hindi": "इस वीडियो में, हम न्यूरल नेटवर्क कंप्यूटर विजन मॉडल को प्रशिक्षित करते हैं।",
    "removed_fillers": ["uh", "basically", "you know"],
    "input_word_count": 12,
    "output_word_count": 12,
    "notes": "Disfluencies removed and sentence syntax restored with proper SOV grammar in Hindi. Filtered verbal fillers: uh, basically, you know."
  }
  ```

### 2. Compress Paragraph to 35%–40% Précis
- **Endpoint:** `POST /api/precis`
- **Request Body:**
  ```json
  {
    "text": "Welcome back guys, in this particular tutorial today, what we are basically going to do is explore how deep learning and artificial neural networks actually work under the hood. You know, many people think that neural networks are like a magic black box, but actually, it is just basic linear algebra, matrix multiplication, and calculus with gradient descent. We will take a sample dataset of images, write a Python script using PyTorch, and see how the loss function decreases step by step until the computer learns to classify cats and dogs accurately.",
    "min_ratio": 0.35,
    "max_ratio": 0.40,
    "target_language": "hindi"
  }
  ```
- **Response Body:**
  ```json
  {
    "original_text": "...",
    "original_word_count": 92,
    "precis_english": "Today, explore how deep learning and artificial neural networks actually work under the hood. It is just basic linear algebra, matrix multiplication. We will take a sample dataset of images, write a Python script using PyTorch.",
    "precis_hindi": "आज, पता लगाएँ कि डीप लर्निंग और आर्टिफ़िशियल न्यूरल नेटवर्क वास्तव में हुड के नीचे कैसे काम करते हैं। यह सिर्फ बुनियादी रैखिक बीजगणित, मैट्रिक्स गुणा है। हम छवियों का एक नमूना डेटासेट लेंगे, PyTorch का उपयोग करके एक पायथन स्क्रिप्ट लिखेंगे।",
    "precis_word_count": 36,
    "retention_ratio_pct": 39.1,
    "target_ratio_range": "35% - 40%",
    "is_within_budget": true,
    "key_points_retained": ["neural", "networks", "step", "explore", "deep"]
  }
  ```

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

