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
    DOC["Standard PDF / Word Documents"]
    INGEST["Stage 6: Syntax Learning Engine (pypdf / Flan-T5)"]
    ASR_IN["Stage 2: Raw Speech Transcript (faster-whisper)"]
    REFORM["Stage 5: Meaningful Sentence Restorer (SOV Hindi)"]
    COMPRESS["Stage 5: 35%-40% Précis Compression"]
    SYNTH["Downstream: Neural Voice Synthesis & HLS Multi-Track"]

    DOC --> INGEST
    INGEST -.->|Canonical Syntax Constraints| REFORM
    ASR_IN --> REFORM
    REFORM --> COMPRESS
    COMPRESS --> SYNTH

    linkStyle default stroke:#0284C7,stroke-width:2.5px;

    classDef stageNode fill:#1E293B,stroke:#0284C7,stroke-width:2px,color:#FFFFFF;
    classDef finalNode fill:#064E3B,stroke:#10B981,stroke-width:2.5px,color:#FFFFFF;

    class DOC,INGEST,ASR_IN,REFORM,COMPRESS stageNode;
    class SYNTH finalNode;
```

---

### Directive 1: Sentence Reformation (Contextual Restructuring) — [Completed: Stage 5]

- **Status:** **Completed** in [`5. Sentence Reformation/`](5.%20Sentence%20Reformation/README.md)
- **Implemented Capabilities:**
  - Removes verbal fillers (*um, uh, basically, you know*) and false speech starts.
  - Reconstructs Subject-Verb-Object (SVO, English) into natural Subject-Object-Verb (SOV, Indic languages like Hindi/Bengali).
  - Automatically inserts Hindi case markers (*ne, ko, se, mein*) and restores predicate coherence.

---

### Directive 2: Sentence Training Engine (Document/PDF Ingestion) — [Completed: Stage 6]

- **Status:** **Completed** in [`6. Sectence Construction/`](6.%20Sectence%20Construction/README.md)
- **Implemented Capabilities:**
  - PDF/DOCX text extraction using `pypdf` and `python-docx`.
  - Self-supervised synthetic corruption engine (`SentenceCorrupter`) applying word jumbling, function word dropping, and grammatical inflection distortion.
  - Seq2Seq Transformer fine-tuning pipeline on Google Flan-T5 with multi-beam search decoding in `construct.py`.

---

### Directive 3: Useful-to-Short Sentence Compression (Duration Budgeting) — [Completed: Stage 5 & Ongoing]

- **Status:** **Core Engine Completed** in [`5. Sentence Reformation/`](5.%20Sentence%20Reformation/README.md)
- **Implemented Capabilities & Next Steps:**
  - Enforces strict 35%–40% word budget window:
    $$\lfloor 0.35 \times W_{\text{orig}} \rfloor \le W_{\text{precis}} \le \lceil 0.40 \times W_{\text{orig}} \rceil$$
  - Prevents speech overflow when translated Indic syllables exceed the original video duration window.
  - Next milestone: Dynamic phoneme-level duration matching with millisecond speech timestamps.

---

### Directive 4: YouTube-Style Decoupled Multi-Audio Track Delivery (HLS/DASH) — [Upcoming Milestone]

- **Status:** **In Design & Implementation**
- **Target Milestones:**
  - Zero video re-encoding: Keeps the master video track untouched and streams dubbed speech on secondary AAC audio tracks linked through an HLS manifest (`master.m3u8`).
  - Seamless buffer-free language switching in frontend HTML5 video players.
  - Multi-speaker voice cloning and pitch-preserving gender-matched neural TTS synthesis.

---

## 👥 Authors & Academic Context

- **Student Contributors:** Atanu Saha, Babin Bid, Rohit Kr Adak, Sagnik Bachhar
- **Faculty Guide:** Dr. Debjit Ghosh (Department of Computer Science & Engineering)
- **Suite:** Nativox Modular Real-Time AI Multilingual Dubbing Suite

---

<p align="center">
  <a href="README.md">🏠 Suite Overview</a> &bull; <a href="ARCHITECTURE.md">🏛️ Architecture</a> &bull; <a href="INSTRUCTIONS.md">📖 Instructions</a> &bull; <a href="ROADMAP.md">🗺️ Roadmap</a>
</p>

<p align="center">
  <sub><b>Nativox</b> &bull; Real-Time AI Multilingual Dubbing Suite &bull; <b>End of Roadmap Specification</b></sub>
</p>
