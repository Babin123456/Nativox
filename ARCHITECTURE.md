# Nativox Architecture & Modular Pipeline Design

This document details the modular component architecture of **Nativox**, tracking how each standalone stage interfaces with the pipeline to deliver real-time, contextually accurate video dubbing.

[![Suite Readme](https://img.shields.io/badge/Suite_Readme-📖_README.md-009688?style=for-the-badge&logo=readme&logoColor=white)](README.md)
[![Instructions](https://img.shields.io/badge/Instructions-📖_INSTRUCTIONS.md-3E8FC4?style=for-the-badge&logo=googledocs&logoColor=white)](INSTRUCTIONS.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-🔮_ROADMAP.md-9B51E0?style=for-the-badge&logo=compass&logoColor=white)](ROADMAP.md)
[![MIT License](https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white)](LICENSE.md)

---

## 🏛️ High-Level Component Flow

```mermaid
graph TD
    VID["🎬 Input Video (.mp4 / .mov)"]
    
    subgraph S1["Stage 1: Audio Extraction & Separation"]
        EXTRACT["FFmpeg Audio Extractor"]
        DEMUCS["Demucs Vocal / Ambience Splitter"]
    end
    
    subgraph S2["Stage 2: Speech Recognition & Gender Pitch"]
        WHISPER["OpenAI Whisper / Faster-Whisper"]
        PITCH["Acoustic Pitch & Formant Analyzer"]
    end
    
    subgraph S3["Stage 3: Terminology & Keyword Extraction"]
        KEYBERT["KeyBERT / spaCy Entity Extraction"]
    end
    
    subgraph S4["Stage 4: Multilingual Terminology Mapping"]
        TRANS_KW["Contextual Keyword Translation"]
    end
    
    subgraph S5["Stage 5: Reformation & Duration Budgeting"]
        REFORM["Spoken Disfluency Cleaner (Ollama / LLM)"]
        COMPRESS["Semantic Syllable & Character Budgeting"]
    end
    
    subgraph S6["Stage 6: Voice Synthesis & Delivery"]
        TTS["Edge-TTS / XTTS-v2 Voice Cloning"]
        STITCH["FFmpeg Overlap-Safe Audio Multiplexer"]
        HLS["Decoupled Multi-Track HLS / DASH Packager"]
    end

    VID --> EXTRACT
    EXTRACT --> DEMUCS
    DEMUCS -->|Isolated Vocals| WHISPER
    DEMUCS -->|Reference Clip| PITCH
    WHISPER -->|Timestamped Segments| KEYBERT
    KEYBERT --> TRANS_KW
    WHISPER --> REFORM
    TRANS_KW -.->|Domain Lexicon| REFORM
    REFORM --> COMPRESS
    COMPRESS --> TTS
    PITCH -->|"Gender Tag (M/F)"| TTS
    TTS --> STITCH
    DEMUCS -->|Preserved Background Bed| STITCH
    STITCH --> HLS
    HLS --> DUBBED["🎧 YouTube-Style Multi-Track Stream"]

    style S1 fill:#152530,stroke:#3E8FC4,stroke-width:2px,color:#EDEDE6
    style S2 fill:#14171C,stroke:#3E8FC4,stroke-width:2px,color:#EDEDE6
    style S3 fill:#3A2E18,stroke:#E8A33D,stroke-width:2px,color:#EDEDE6
    style S4 fill:#2E1A2E,stroke:#B06AE0,stroke-width:2px,color:#EDEDE6
    style S5 fill:#2E1A1A,stroke:#D96257,stroke-width:2px,color:#EDEDE6
    style S6 fill:#1A2E1A,stroke:#4FAE7A,stroke-width:2px,color:#EDEDE6
```

---

## 🔍 Stage Specifications

### 1. Stage 1: `1. mp4 to mp3/`

- **Responsibility:** Ingest incoming media and decouple audio streams.
- **Port:** `8000` (standalone)
- **Core Operations:**
  - FFmpeg audio extraction (`-vn -acodec libmp3lame -q:a 2`).
  - Vocal and background instrumental separation.

### 2. Stage 2: `2. mp3 to Text/`

- **Responsibility:** High-precision acoustic transcription and speaker feature extraction.
- **Port:** `8001` (standalone)
- **Core Operations:**
  - Whisper ASR with millisecond start/end timestamps per sentence segment.
  - Formant and pitch detection for automatic gender identification (Male/Female voice selection).

### 3. Stage 3: `3. Text to Keyword/`

- **Responsibility:** Identify technical vocabulary and domain terms that require specialized translation.
- **Port:** `8002` (standalone)
- **Core Operations:**
  - KeyBERT sentence-transformers embeddings with MMR (Maximal Marginal Relevance) diversification.
  - Filtering stopwords and highlighting critical technical jargon.

### 4. Stage 4: `4. Keyword Translate/`

- **Responsibility:** Multilingual glossary resolution.
- **Port:** `8003` (standalone)
- **Core Operations:**
  - Translates isolated domain entities and noun phrases.
  - Guarantees technical words (e.g. "Transformer", "Backpropagation") are either preserved in English or matched to accepted standardized vernacular terms.

### 5. Stage 5: `5. Sentence Reformation/`

- **Responsibility:** Spoken disfluency cleaning, syntax restoration, and duration-budgeted 35%–40% précis compression (English to Hindi).
- **Port:** `8012` (standalone)
- **Core Operations:**
  - Removal of spoken disfluencies (*um, uh, you know, like*) and predicate restructuring (SVO to Indic SOV).
  - Algorithmic précis compression reducing full MP3 transcript paragraphs to 35%–40% length while preserving semantic integrity and core technical facts.
  - Contextual Hindi translation with proper postpositions (*vibhakti*) and grammatical case markers.

---

## ⚡ Integration into Unified Delivery

While each stage runs independently for research evaluation and testing, the modular pipeline stages chain together with asynchronous job management, real-time status events, and decoupled HLS output generation.
