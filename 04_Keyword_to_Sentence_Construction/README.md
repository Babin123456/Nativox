# Stage 4: Keyword to Sentence Construction

## Document-Trained Sequence-to-Sequence Syntax Reconstruction Engine

Part of the **Nativox** AI Multilingual Dubbing Suite.

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="../README.md"><img src="https://img.shields.io/badge/Nativox_Suite-⬅️_Back_to_Suite-009688?style=for-the-badge&logo=readme&logoColor=white" alt="Nativox Suite" /></a>
  <a href="../03_Text_to_Keyword/README.md"><img src="https://img.shields.io/badge/Prev_Stage-Stage_3:_Keywords-3E8FC4?style=for-the-badge&logo=fastapi&logoColor=white" alt="Previous Stage" /></a>
  <a href="../05a_Keyword_Translation__Sagnik/README.md"><img src="https://img.shields.io/badge/Next_Stage-Stage_5:_Translation-FF6B6B?style=for-the-badge&logo=fastapi&logoColor=white" alt="Next Stage" /></a>
  <a href="../ARCHITECTURE.md"><img src="https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-E8A33D?style=for-the-badge&logo=blueprint&logoColor=white" alt="Architecture" /></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11" /></a>
  <a href="https://pytorch.org"><img src="https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch 2.0+" /></a>
  <a href="https://huggingface.co"><img src="https://img.shields.io/badge/Transformers-Seq2Seq-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face Transformers" /></a>
</p>

---

## 📖 Operational Overview

In spoken speech transcription, noisy OCR, and second-language drafting, input text often arrives in a **destructive** state:

- **Jumbled word order:** Tokens appear out of place (e.g., Object-Verb-Subject scrambles).
- **Omitted function words:** Missing articles (*a, an, the*), prepositions (*in, on, to*), and auxiliary verbs (*is, are, was*).
- **Broken grammatical agreement:** Distorted singular/plural inflections and verb tenses.
- **Missing casing and punctuation:** Completely unpunctuated lowercase streams.

Stage 4 learns canonical sentence syntax directly from standard **PDF (`.pdf`)** or **Word (`.docx`)** documents, trains a Sequence-to-Sequence (Seq2Seq) Transformer model using self-supervised synthetic corruption, and provides an inference engine to transform any destructive input sentence into a constructive, meaningful sentence.

---

## 🛠️ Tech Stack: Architectural Rationale & Comparative Evaluation

| Technology | Purpose in Pipeline | Why It Is Chosen Over Existing Alternatives | Viable Alternatives & Trade-Off Analysis |
| :--- | :--- | :--- | :--- |
| **Google Flan-T5 (`flan-t5-small` / `base`)** | Sequence-to-Sequence encoder-decoder restoring broken token order and grammar | Instruction-finetuned text-to-text architecture naturally excels at structural rewriting, token insertion, and grammatical re-ordering without hallucinating extraneous facts. Compact size (300MB weights) allows local fine-tuning on consumer hardware and low-latency CPU inference. | **OpenAI GPT-4 / Anthropic Claude API:** Requires continuous cloud connectivity, introduces 500ms–2s API latency, carries recurring per-token inference charges, and risks hallucinating new non-existent facts into scientific transcripts. <br>**BART / mBART:** Higher parameter count with slower inference; Flan-T5 produces tighter syntactic reconstructions. |
| **PyTorch 2.0+ & Hugging Face Transformers** | Model training, self-supervised corruption loss, and beam-search generation | Industry standard deep-learning ecosystem with native mixed-precision (FP16/BF16), efficient gradient accumulation, and modular Seq2Seq training APIs (`Seq2SeqTrainer`). | **TensorFlow / Keras:** Steeper boilerplate for sequence-to-sequence beam search customization; less vibrant open-source Hugging Face model ecosystem. |
| **`pypdf` & `python-docx`** | Direct document corpus text extraction | Pure-Python, headless parsers capable of ingesting PDF textbooks and DOCX manuals locally with zero external binary or OS-level dependencies. | **PyMuPDF / pdfminer.six:** PyMuPDF requires external AGPL C-libraries that complicate commercial distribution; pdfminer is significantly slower on large 500-page textbooks. |
| **Beam Search Decoding (`num_beams=4`)** | Constrained probability decoding with repetition penalty and length penalty | Explores multiple generation paths concurrently, eliminating cyclic loops and ensuring restored sentences maintain natural cadence. | **Greedy Search:** Fast but prone to grammatical traps and repetitive token loops. <br>**Top-p / Top-k Sampling:** Introduces non-deterministic stochastic variations undesirable for precise academic dubbing. |

---

## 📋 Prerequisites & Requirements

- **Python:** **3.11** (Repository pinned via root `.python-version`)
- **Dependencies:** `torch`, `transformers`, `pypdf`, `python-docx`, `tqdm`
- **CUDA:** Optional but recommended for faster training on GPU

---

## 🚀 Setup & Execution

### 1. Navigate to Stage Directory

```bash
cd 04_Keyword_to_Sentence_Construction
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

- **Activate on Windows (Git Bash):**

  ```bash
  source venv/Scripts/activate
  ```

- **Activate on macOS / Linux:**

  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Web Application or Interactive CLI

- **Launch Full Web Interface (Recommended):**

  ```bash
  python -m uvicorn main:app --reload --port 8004
  ```

  Open your browser at **`http://127.0.0.1:8004`**.

- **Launch Interactive Testing CLI:**

  ```bash
  python construct.py
  ```

- **Train Seq2Seq Model on Document Corpus (Optional):**

  ```bash
  python train.py
  ```

---

## 🏛️ Pipeline Architecture

```text
                                  [Training Pipeline]
                                  
+-----------------------------+       +-----------------------------+
|   Normal PDF / Word Files   | ----> |    Document Text Parser     |
|   (.pdf, .docx, .txt)       |       |   (pypdf / python-docx)     |
+-----------------------------+       +-----------------------------+
                                                     |
                                                     v
+-----------------------------+       +-----------------------------+
|    Destructive Synthesizer  | <---- |    Sentence Segmenter       |
|    - Word Order Jumbling    |       |  (Clean, Well-Formed Units) |
|    - Function Word Dropping |       +-----------------------------+
|    - Agreement / Noise      |
+-----------------------------+
               |
               v
+-----------------------------+       +-----------------------------+
|  Paired Supervised Dataset  | ----> | Seq2Seq Transformer (T5)    |
|(Destructive -> Constructive)|       | Fine-Tuning & Checkpoint    |
+-----------------------------+       +-----------------------------+
                                                     |
                                                     v
                                              ./saved_model
                                                     |
                                  [Inference / Testing]
                                                     v
+-----------------------------+       +-----------------------------+       +-----------------------------+
|  User Destructive Sentence  | ----> |      construct.py           | ----> |    Constructive Sentence    |
| "market went yesterday she" |       | (Beam Search Decoder)       |       | "She went to the market..." |
+-----------------------------+       +-----------------------------+       +-----------------------------+
```

---

## 🔌 CLI & Usage Guide

### Step 1: Train the Model (`train.py`)

Train the model directly on your PDF document (e.g. `sample_text.pdf`):

```bash
# Auto-detects sample_text.pdf in the directory and trains:
python train.py

# Or explicitly pass the path and hyperparameters:
python train.py --data_path sample_text.pdf --epochs 12 --batch_size 8
```

#### Key Training Arguments

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--data_path` | `None` (auto-detect) | Path to `.pdf`, `.docx`, `.txt` file, or directory |
| `--model_name` | `google/flan-t5-small` | Base Seq2Seq model (`google/flan-t5-small`, `google/flan-t5-base`, etc.) |
| `--output_dir` | `./saved_model` | Directory to save trained model weights & tokenizer |
| `--epochs` | `5` | Number of training epochs |
| `--batch_size` | `16` | Training batch size (auto-scaled on GPU/CPU) |
| `--lr` | `3e-4` | Learning rate for AdamW optimizer |
| `--augmentations_per_sentence` | `5` | Number of destructive variants generated per clean sentence |

### Step 2: Test Sentence Construction (`construct.py`)

`construct.py` supports three versatile modes:

#### Mode 1: Interactive Live CLI (Default)

Run interactive testing to enter destructive sentences and see real-time constructive outputs:

```bash
python construct.py
```

```text
[*] NATIVOX: INTERACTIVE SENTENCE CONSTRUCTION TESTING
Enter any destructive sentence (e.g., scrambled words, broken grammar).
Type 'exit', 'quit', or 'q' to stop.

Destructive Input > artificial intelligence world changing rapidly is

Constructive Output > Artificial intelligence is rapidly changing the world.
[Latency: 38.2ms | Beams: 4]
```

#### Mode 2: Single Sentence Command-Line Argument

```bash
python construct.py --sentence "plants sunlight into chemical energy convert photosynthesis"
```

Output:

```text
======================================================================
[*] SENTENCE CONSTRUCTION RESULT
======================================================================
- DESTRUCTIVE INPUT   : plants sunlight into chemical energy convert photosynthesis
- CONSTRUCTIVE OUTPUT : Photosynthesis converts sunlight into chemical energy.
- INFERENCE TIME      : 42.1 ms
```

---

### Verification Benchmark Results

| # | Destructive Input (Jumbled / Broken) | Constructive Output (Fluent & Meaningful) |
| :--- | :--- | :--- |
| 1 | `artificial intelligence world changing rapidly is` | **Artificial intelligence is rapidly changing the world.** |
| 2 | `plants sunlight into chemical energy convert photosynthesis` | **Photosynthesis converts sunlight into chemical energy.** |
| 3 | `effective communication organizations modern cornerstone essential is` | **Effective communication is an essential cornerstone of modern organizations.** |
| 4 | `deep networks learn complex patterns massive datasets from` | **Deep networks learn complex patterns from massive datasets.** |
| 5 | `delivered software team schedule ahead project of the` | **The software team delivered the software ahead of the project schedule.** |
| 6 | `sun around revolve planets eight the` | **The sun revolves around eight planets.** |
| 7 | `market went yesterday she to the` | **She went to the market yesterday.** |
| 8 | `apple eating boy an is oak tree under` | **An apple is under an oak tree.** |

---

## 📁 Project Structure

```text
04_Keyword_to_Sentence_Construction/
├── data_utils.py               # Document extractors (PDF/Word), sentence splitter, corruption engine
├── train.py                    # Seq2Seq Transformer training pipeline (T5 fine-tuning)
├── construct.py                # Testing & inference engine (interactive, CLI, & batch modes)
├── requirements.txt            # Dependencies (torch, transformers, pypdf, python-docx, tqdm)
├── sample_text.pdf             # User PDF dataset (164 pages)
├── saved_model/                # Trained model checkpoint and tokenizer weights
└── README.md                   # Complete module documentation
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
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Module 4 Documentation</b></sub>
</p>
<!-- markdownlint-enable MD033 -->
