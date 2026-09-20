# Nativox Architecture & Modular Pipeline Design

This document details the modular component architecture of **Nativox**, tracking how each standalone stage interfaces with the pipeline to deliver real-time, contextually accurate video dubbing.

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Suite_Readme-📖_README.md-009688?style=for-the-badge&logo=readme&logoColor=white" alt="Suite Readme" /></a>
  <a href="INSTRUCTIONS.md"><img src="https://img.shields.io/badge/Instructions-📖_INSTRUCTIONS.md-3E8FC4?style=for-the-badge&logo=googledocs&logoColor=white" alt="Instructions" /></a>
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white" alt="Roadmap" /></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white" alt="MIT License" /></a>
</p>
<!-- markdownlint-enable MD033 -->

---

## 🏛️ High-Level Component Flow

```mermaid
graph TD
    VID["Input Video (.mp4 / .mov / .mkv)"]
    
    subgraph S1["Stage 1: Audio Extraction & Isolation"]
        EXTRACT["FFmpeg Audio Extractor (libmp3lame)"]
        DEMUCS["Vocal & Ambience Demuxer"]
    end
    
    subgraph S2["Stage 2: Speech Recognition (ASR)"]
        WHISPER["faster-whisper Engine (CTranslate2)"]
        VAD["Silero Voice Activity Detector"]
    end
    
    subgraph S3["Stage 3: Salient Keyword Extraction"]
        RAKE["Multilingual RAKE Co-occurrence Matrix"]
        SCRIPT_TAG["Unicode Script Tagger (En / Hi / Bn)"]
    end
    
    subgraph S4["Stage 4: Sentence Construction & Syntax Restoration"]
        DOC_INGEST["Document Parser (pypdf / python-docx)"]
        CORRUPT["Synthetic Noise Generator"]
        T5_TRAIN["Flan-T5 Seq2Seq Model & Beam Search"]
    end

    subgraph S5a["Stage 5(a): Terminology Translation"]
        TRANS_KW["deep-translator Batch Engine"]
        PHONETIC["indic-transliteration (ITRANS)"]
    end
    
    subgraph S5b["Stage 5(b): Reformation & Précis Compression"]
        REFORM["Disfluency Cleaner & SOV Restorer"]
        COMPRESS["35%-40% Word Budget Précis Engine"]
    end

    subgraph S6["Stage 6: Hindi Text → MP3 Speech Synthesis"]
        TTS["Edge Neural TTS (hi-IN voices)"]
        PROSODY["Rate & Pitch Prosody Control"]
        MP3OUT["MP3 Audio File Generator"]
    end

    subgraph S7["Stage 7: Final Dubbed Video Assembly"]
        REMUX["FFmpeg Copy-Mode Remux (-c:v copy)"]
        STRIP["Original Audio Removal (-map 0:v:0)"]
        ATTACH["Dubbed AAC Audio Attach (-c:a aac)"]
    end

    VID --> EXTRACT
    EXTRACT --> DEMUCS
    DEMUCS -->|Isolated Vocals| VAD
    VAD --> WHISPER
    WHISPER -->|Timestamped Segments| RAKE
    RAKE --> SCRIPT_TAG
    SCRIPT_TAG --> TRANS_KW
    TRANS_KW --> PHONETIC
    SCRIPT_TAG --> T5_TRAIN
    DOC_INGEST --> CORRUPT
    CORRUPT --> T5_TRAIN
    WHISPER --> REFORM
    TRANS_KW -.->|Domain Lexicon| REFORM
    REFORM --> COMPRESS
    COMPRESS --> TTS
    T5_TRAIN --> TTS
    TTS --> PROSODY
    PROSODY --> MP3OUT
    MP3OUT --> REMUX
    VID -.->|Original Video Frames| REMUX
    REMUX --> STRIP
    STRIP --> ATTACH
    ATTACH --> DUBBED["Final Dubbed MP4"]

    linkStyle default stroke:#0284C7,stroke-width:2.5px;

    classDef stageNode fill:#1E293B,stroke:#0284C7,stroke-width:2px,color:#FFFFFF;
    classDef finalNode fill:#064E3B,stroke:#10B981,stroke-width:2.5px,color:#FFFFFF;

    class VID,EXTRACT,DEMUCS,WHISPER,VAD,RAKE,SCRIPT_TAG,TRANS_KW,PHONETIC,REFORM,COMPRESS,DOC_INGEST,CORRUPT,T5_TRAIN,TTS,PROSODY,MP3OUT,REMUX,STRIP,ATTACH stageNode;
    class DUBBED finalNode;
```

---

## 🔍 Stage Specifications

### 1. Stage 1: `01_MP4_to_MP3/`

- **Responsibility:** Ingest incoming media and extract pristine audio.
- **Port:** `http://127.0.0.1:8000`
- **Core Operations:**
  - FFmpeg high-bitrate audio extraction (`-vn -acodec libmp3lame -q:a 2`).
  - Web-based side-by-side synchronized video and audio playback preview.

### 2. Stage 2: `02_MP3_to_Text/`

- **Responsibility:** High-precision acoustic transcription with timestamped speech segments.
- **Port:** `http://127.0.0.1:8001`
- **Core Operations:**
  - Silero VAD for non-speech and silence filtering.
  - `faster-whisper` (CTranslate2) with INT8 CPU and FP16 GPU inference.
  - Tri-lingual support with automatic script classification for English, Hindi (Devanagari), and Bengali (Bangla script).

### 3. Stage 3: `03_Text_to_Keyword/`

- **Responsibility:** Extract salient content-bearing keywords and domain terminology.
- **Port:** `http://127.0.0.1:8010`
- **Core Operations:**
  - Multilingual RAKE co-occurrence matrix scoring ($W_{\text{deg}} / W_{\text{freq}}$).
  - Curated joint stopword lists for English, Hindi, and Bengali.
  - Code-mixed spoken sentence processing without language segmentation overhead.

### 4. Stage 4: `04_Keyword_to_Sentence_Construction/`

- **Responsibility:** Document-trained sentence syntax learning and destructive-to-constructive sentence reconstruction.
- **Port:** `http://127.0.0.1:8004` (Web Interface & CLI `construct.py`)
- **Core Operations:**
  - Ingestion of standard PDF (`.pdf`) and Word (`.docx`) documents using `pypdf` and `python-docx`.
  - Self-supervised synthetic corruption (`SentenceCorrupter`): token jumbling, function word dropping, and grammatical inflection noise.
  - Fine-tuning of Google Flan-T5 Seq2Seq Transformer model using AdamW optimizer.
  - Multi-beam search decoding for real-time reconstruction of fragmented input sentences.

### 5. Stage 5(a): `05a_Keyword_Translation__Sagnik/`

- **Responsibility:** Multilingual terminology translation and phonetic guide generation.
- **Port:** `http://127.0.0.1:8011`
- **Core Operations:**
  - `deep-translator` batch terminology mapping with failover resilience.
  - `indic-transliteration` (ITRANS / Harvard-Kyoto) phonetic pronunciation guide synthesis for Indic text.
  - Fast Unicode script detection without expensive model overhead.

### 6. Stage 5(b): `05b_Sentence_Reformation__Atanu/`

- **Responsibility:** Disfluency removal, SOV grammar restoration, and 35%–40% précis compression.
- **Port:** `http://127.0.0.1:8012`
- **Core Operations:**
  - Strips verbal disfluencies (*um, uh, basically, you know*) and restores predicate structure.
  - Enforces the faculty-directed 35%–40% paragraph word budget window:
    $$\lfloor 0.35 \times W_{\text{orig}} \rfloor \le W_{\text{precis}} \le \lceil 0.40 \times W_{\text{orig}} \rceil$$
  - Contextual Hindi translation with proper postpositions (*vibhakti*) and grammatical case markers.

### 7. Stage 6: `06_Converted_Text_to_MP3/`

- **Responsibility:** Convert reformed Hindi text into natural-sounding MP3 speech audio.
- **Port:** `http://127.0.0.1:8013`
- **Core Operations:**
  - Microsoft Edge Neural TTS synthesis via `edge-tts` — zero API keys, zero GPU.
  - Multi-voice selection: female (`hi-IN-SwaraNeural`) and male (`hi-IN-MadhurNeural`) Hindi voices.
  - Prosody control with adjustable speech rate and pitch parameters.
  - Produces standard MP3 files ready for Stage 7 final video assembly.

### 8. Stage 7: `07_Merge_MP3_with_MP4/`

- **Responsibility:** Final dubbed video assembly — merge original video with target-language audio.
- **Port:** `http://127.0.0.1:8014`
- **Core Operations:**
  - FFmpeg copy-mode remux: preserves original video frames byte-for-byte (`-c:v copy`).
  - Completely removes original English audio track (`-map 0:v:0 -map 1:a:0`).
  - Transcodes dubbed MP3 to AAC (`-c:a aac -b:a 192k`) for maximum MP4 container compatibility.
  - FastStart optimization (`-movflags +faststart`) for instant web playback.
  - Duration safety via `-shortest` flag to handle audio/video length mismatches.

---

## ⚡ Integration into Unified Delivery

While each stage runs independently for academic evaluation and unit benchmarking, the modular pipeline stages chain together with asynchronous job management, real-time status events, and decoupled HLS output generation:

1. Stage 1 extracts raw audio from incoming video.
2. Stage 2 transcribes speech into timestamped tokens.
3. Stage 3 isolates domain keywords.
4. Stage 4 reconstructs grammatically sound sentences from keywords using document-trained models.
5. Stage 5(a) maps keywords to the target language and generates phonetic guides.
6. Stage 5(b) removes fillers and compresses paragraphs to a strict 35%–40% duration budget.
7. **Stage 6 synthesizes the reformed Hindi text into natural MP3 speech using Edge Neural TTS.**
8. **Stage 7 merges the original video with the dubbed MP3, replacing the English audio to produce the final dubbed MP4.**

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

---

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="README.md">🏠 Suite Overview</a> &bull; <a href="ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Architecture Specification</b></sub>
</p>
<!-- markdownlint-enable MD033 -->
