# Future Roadmap & Faculty Directives

Faculty Directives and Real-Time YouTube-Style Dubbing Evolution.

[![Suite Readme](https://img.shields.io/badge/Suite_Readme-📖_README.md-009688?style=for-the-badge&logo=readme&logoColor=white)](README.md)
[![Architecture](https://img.shields.io/badge/Architecture-📐_ARCHITECTURE.md-3E8FC4?style=for-the-badge&logo=blueprint&logoColor=white)](ARCHITECTURE.md)
[![Instructions](https://img.shields.io/badge/Instructions-📖_INSTRUCTIONS.md-4FAE7A?style=for-the-badge&logo=googledocs&logoColor=white)](INSTRUCTIONS.md)
[![MIT License](https://img.shields.io/badge/License-📜_MIT-gold?style=for-the-badge&logo=open-source-initiative&logoColor=white)](LICENSE.md)

---

## 📑 Core Faculty Directives & Engineering Milestones

This roadmap outlines the evolution of the **Nativox** suite from standalone modular stages into a real-time, low-latency, streaming multilingual video dubbing platform.

```mermaid
graph TD
    DOC["📚 Bulky Documents / PDFs<br/>(Domain Knowledge Base)"]
    INGEST["⚙️ <b>Module 2: Sentence Train Engine</b><br/>Extraction • Chunking • Semantic Vector Embedding"]
    ASR_IN["🗣️ Raw Whisper ASR Segment"]
    REFORM["🧠 <b>Module 1: Sentence Reformation</b><br/>Grammar Correction • Idiomatic Alignment"]
    COMPRESS["⏱️ <b>Module 3: Useful-to-Short Compression</b><br/>Syllable Fitting • Time Window Budgeting"]
    TTS_OUT["🔊 Neural Voice Synthesis Engine"]

    DOC --> INGEST
    INGEST -.->|Context Embeddings / Few-Shot Prompts| REFORM
    ASR_IN --> REFORM
    REFORM --> COMPRESS
    COMPRESS --> TTS_OUT

    style DOC fill:#14171C,stroke:#E8A33D,stroke-width:1.5px,color:#EDEDE6
    style INGEST fill:#3A2E18,stroke:#E8A33D,stroke-width:2px,color:#EDEDE6
    style ASR_IN fill:#14171C,stroke:#3E8FC4,stroke-width:1.5px,color:#EDEDE6
    style REFORM fill:#152530,stroke:#3E8FC4,stroke-width:2px,color:#EDEDE6
    style COMPRESS fill:#2E1A1A,stroke:#D96257,stroke-width:2px,color:#EDEDE6
    style TTS_OUT fill:#1A2E1A,stroke:#4FAE7A,stroke-width:2px,color:#EDEDE6
```

---

### Directive 1: Sentence Reformation (Contextual Restructuring)
* **Goal:** Convert raw transcribed speech into natural, spoken colloquial syntax.
* **Key Tasks:**
  - Remove speech fillers (*um, uh, you know, like*) and false starts.
  - Reconstruct Subject-Verb-Object (SVO, English) into natural Subject-Object-Verb (SOV, Indic languages like Hindi/Bengali).
  - Match gender and honorific registers (*आप* vs. *तुम*; *আপনি* vs. *তুমি*).

---

### Directive 2: Sentence Training Engine (Document/PDF Ingestion)
* **Goal:** Ingest domain-specific bulky documents (research papers, textbooks, scripts) so technical terms are accurately translated.
* **Key Tasks:**
  - PDF/DOCX text extraction using `pypdf` and semantic sliding-window chunking.
  - ChromaDB / FAISS vector database embedding for real-time terminology retrieval (RAG).
  - Retain specialized nomenclature in source English or officially accepted vernacular translations.

---

### Directive 3: Useful-to-Short Sentence Compression (Duration Budgeting)
* **Goal:** Prevent speech overflow and overlap when translated sentences require more syllables than the video time gap allows.
* **Key Tasks:**
  - Calculate segment duration budget: $T = \text{segment.end} - \text{segment.start}$.
  - Compute maximum allowable characters based on natural speaking rate ($\sim 14$ characters/second).
  - Dynamically prompt compact LLM rewriting to fit the exact millisecond time window without robotic `atempo` warping.

---

### Directive 4: YouTube-Style Decoupled Multi-Audio Track Delivery (HLS/DASH)
* **Goal:** Zero video re-encoding and instant, buffer-free language switching in the player.
* **Key Tasks:**
  - Keep the original master video track untouched.
  - Stream dubbed speech on secondary AAC audio tracks linked through an HLS manifest (`master.m3u8`).
  - Allow instant audio language switching in frontend video players.
