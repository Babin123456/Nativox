# Nativox Stage 6: Sentence Construction & Syntax Restoration

A deep learning pipeline for learning sentence syntax from standard PDF or Word documents and reconstructing destructive, disordered, or broken sentences into fluent, constructive, and meaningful English sentences.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org)
[![HuggingFace Transformers](https://img.shields.io/badge/Transformers-Seq2Seq-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co)

---

## 📖 Overview

In spoken audio transcription, noisy OCR, or second-language drafting, raw text often appears in a **destructive** state:
- Jumbled word order (e.g., Object-Verb-Subject or Subject-Object-Verb scrambles).
- Omitted function words (articles *a, an, the*, prepositions *in, on, to*, auxiliaries *is, are, was*).
- Broken grammatical inflection and subject-verb agreements.
- Stripped punctuation and flat lowercase casing.

This module learns how meaningful sentences are structured directly from your **standard PDF (`.pdf`) or Word (`.docx`) documents**, trains a Sequence-to-Sequence (Seq2Seq) Transformer model, and provides an inference engine to transform any destructive input sentence into a constructive, meaningful sentence.

---

## 🏛️ Pipeline Architecture

```
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
| (Destructive -> Constructive|       | Fine-Tuning & Checkpoint    |
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

## 📂 File Structure

```
6. Sectence Construction/
├── data_utils.py               # Document extractors (PDF/Word), sentence splitter, corruption engine
├── train.py                    # Seq2Seq Transformer training pipeline (T5 fine-tuning)
├── construct.py                # Testing & inference engine (interactive, CLI, & batch modes)
├── requirements.txt            # Dependencies (torch, transformers, pypdf, python-docx, tqdm)
├── sample_text.pdf             # User PDF dataset (164 pages)
├── saved_model/                # Trained model checkpoint and tokenizer weights
└── README.md                   # Complete module documentation
```

---

## ⚙️ Installation

1. Ensure Python 3.10+ and CUDA (optional but recommended for GPU acceleration) are installed.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Quick Start Guide

### Step 1: Train the Model (`train.py`)
Train the model directly on your PDF document (e.g. `sample_text.pdf`):

```bash
# Auto-detects sample_text.pdf in the directory and trains:
python train.py

# Or explicitly pass the path and hyperparameters:
python train.py --data_path sample_text.pdf --epochs 12 --batch_size 8
```

#### Key Training Arguments:
| Argument | Default | Description |
| :--- | :--- | :--- |
| `--data_path` | `None` (auto-detect) | Path to `.pdf`, `.docx`, `.txt` file, or directory |
| `--model_name` | `google/flan-t5-small` | Base Seq2Seq model (`google/flan-t5-small`, `google/flan-t5-base`, etc.) |
| `--output_dir` | `./saved_model` | Directory to save trained model weights & tokenizer |
| `--epochs` | `5` | Number of training epochs |
| `--batch_size` | `16` | Training batch size (auto-scaled on GPU/CPU) |
| `--lr` | `3e-4` | Learning rate for AdamW optimizer |
| `--augmentations_per_sentence` | `5` | Number of destructive variants generated per clean sentence |

### Step 3: Test Sentence Construction (`construct.py`)

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
======================================================================
```

#### Mode 3: Batch File Processing
Construct sentences for an entire file (one destructive sentence per line):

```bash
python construct.py --batch_file test_destructive_sentences.txt
```

---

## 🎯 Verification Benchmark Results

Below are actual results produced by the fine-tuned model:

| # | Destructive Input (Jumbled / Broken) | Constructive Output (Fluent & Meaningful) |
| :---: | :--- | :--- |
| 1 | `artificial intelligence world changing rapidly is` | **Artificial intelligence is rapidly changing the world.** |
| 2 | `plants sunlight into chemical energy convert photosynthesis` | **Photosynthesis converts sunlight into chemical energy.** |
| 3 | `effective communication organizations modern cornerstone essential is` | **Effective communication is an essential cornerstone of modern organizations.** |
| 4 | `deep networks learn complex patterns massive datasets from` | **Deep networks learn complex patterns from massive datasets.** |
| 5 | `delivered software team schedule ahead project of the` | **The software team delivered the software ahead of the project schedule.** |
| 6 | `sun around revolve planets eight the` | **The sun revolves around eight planets.** |
| 7 | `market went yesterday she to the` | **She went to the market yesterday.** |
| 8 | `apple eating boy an is oak tree under` | **An apple is under an oak tree.** |

---

## 💡 How it Understands Sentence Formation

1. **Document Ground Truth**: When ingesting PDF or Word documents, the parser extracts well-formed sentences written with correct subject-verb-object (SVO) sequence, accurate prepositional phrases, and proper punctuation.
2. **Self-Supervised Destruction (`SentenceCorrupter`)**: The model is taught the rules of grammar by exposing it to synthetically destroyed versions of clean sentences:
   - *Jumble noise*: Shuffles token order to destroy clause boundaries.
   - *Omission noise*: Drops function words (articles, auxiliary verbs, prepositions) forcing the model to infer missing grammatical glue.
   - *Inflection noise*: Distorts verb forms and plurals.
3. **Seq2Seq Mapping**: The Transformer learns an attention-based mapping from fragmented, disorderly token sequences to complete, capitalized, punctuated, and grammatically harmonious sentences.
