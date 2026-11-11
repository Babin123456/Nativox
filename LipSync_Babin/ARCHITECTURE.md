<!-- markdownlint-disable -->

# Nativox: System Architecture & Workflow Diagrams

> **Creator & Lead Architect**: Babin Bid  
> This document details the multi-stage architecture of the **Nativox Zero-API Multilingual Video Dubbing Pipeline** using comprehensive Mermaid flowcharts and sequence diagrams.

---

## 1. High-Level Pipeline Architecture

```mermaid
flowchart TD
    subgraph INGESTION["Stage 1: Media Ingestion & Stem Disentanglement"]
        InputVideo["Input English Video (.mp4)"] --> Probe["FFprobe Video Diagnostics<br/>(FPS, PTS, Resolution, SAR)"]
        InputVideo --> Demucs["Meta HTDemucs Neural Stem Separation"]
        Demucs --> Vocals["Isolated Speech Track<br/>(source_vocals.wav)"]
        Demucs --> BGM["Preserved Continuous BGM Track<br/>(source_bgm.wav)"]
    end

    subgraph ASR_NLP["Stage 2 & 3: ASR & Syllable-Constrained Translation"]
        Vocals --> Whisper["Local OpenAI Whisper ASR<br/>(Zero-API Timestamped Transcription)"]
        Whisper --> Transcript["English Transcript"]
        Transcript --> SyllableLLM["Syllable-Budgeted Indic Translator<br/>(Google GTX / DeepTranslator - ~3.0 syl/sec)"]
        SyllableLLM --> Translated["Colloquial Hindi / Bengali Dialogue"]
    end

    subgraph VOICE_TRANSFER["Stage 4: Voice Synthesis & Timbre Transfer"]
        Translated --> EdgeTTS["Microsoft Edge-TTS Neural Synthesis<br/>(Zero-Key Native Indic Phonetics)"]
        EdgeTTS --> RawTTS["Raw Synthesized Dialogue"]
        RawTTS & Vocals --> ToneTransfer["OpenVoice V2 + Praat PSOLA<br/>(Transfers Speaker F0, Formants & Timbre)"]
        ToneTransfer --> MorphedSpeech["Speaker-Cloned Dialogue"]
        MorphedSpeech --> Aligner["Duration Aligner (atempo filter)<br/>(Locks to Exact Video Duration)"]
        Aligner & BGM --> MasterAudio["Master Audio Multiplexer (amix)<br/>(Dialogue + Continuous Background Track)"]
    end

    subgraph LIPSYNC["Stage 5 & 6: Lip Sync & Face Restoration"]
        InputVideo & Aligner --> Wav2Lip["Wav2Lip GAN<br/>(Phoneme-Conditioned Lip Dynamics)"]
        Wav2Lip --> RawVideo["Mouth-Synthesized Video Frames"]
        RawVideo & InputVideo --> Compositor["Selective Landmark Mask + GFPGAN v1.4<br/>(Sub-Nasal Cutoff, Untouched Eyes/Face/BG)"]
        Compositor & MasterAudio --> FinalMux["FFmpeg CRF 17 Lossless AV Muxer"]
    end

    subgraph OUTPUT["Stage 7: Quality Evaluation & Delivery"]
        FinalMux --> FinalVideo["Final Dubbed Video (.mp4)"]
        FinalVideo --> WebUI["Web UI Player & Local Output Folder"]
    end
```

---

## 2. Complete Sequence Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Web UI
    participant Web as FastAPI (web/app.py)
    participant Pipe as Pipeline Orchestrator (pipeline.py)
    participant Demucs as Meta HTDemucs Separator
    participant ASR as Local Whisper ASR
    participant Translator as Syllable Translator
    participant TTS as Edge-TTS Adapter
    participant Tone as Tone Transfer Bridge (PSOLA)
    participant Aligner as Duration Aligner
    participant Wav2Lip as Wav2Lip GAN Engine
    participant GFPGAN as Face Restorer & Compositor

    User->>Web: Upload talking-head video (.mp4) & select language (hi/bn)
    Web->>Pipe: Initialize PipelineConfig with Zero-API mode
    
    rect rgb(240, 248, 255)
    Note over Pipe,Demucs: Stage 1: Stem Disentanglement
    Pipe->>Demucs: Separate source audio
    Demucs-->>Pipe: Return clean vocals & continuous BGM
    end

    rect rgb(255, 250, 240)
    Note over Pipe,Translator: Stage 2 & 3: ASR & Translation
    Pipe->>ASR: Transcribe clean vocals (Zero-API Whisper)
    ASR-->>Pipe: Return English transcript
    Pipe->>Translator: Translate text with syllable constraints
    Translator-->>Pipe: Return natural Hindi / Bengali dialogue
    end

    rect rgb(240, 255, 240)
    Note over Pipe,Aligner: Stage 4: Voice Synthesis & Timbre Transfer
    Pipe->>TTS: Synthesize Indic dialogue (Zero-API Edge-TTS)
    TTS-->>Pipe: Return native synthetic speech
    Pipe->>Tone: Transfer original speaker pitch & formant resonances
    Tone-->>Pipe: Return speaker-cloned dubbed dialogue
    Pipe->>Aligner: Match audio duration to video timeline
    Aligner-->>Pipe: Return duration-aligned dialogue
    Pipe->>Pipe: Mix dialogue with continuous BGM
    end

    rect rgb(255, 245, 245)
    Note over Pipe,GFPGAN: Stage 5 & 6: Lip Sync & Face Compositing
    Pipe->>Wav2Lip: Generate mouth motion conditioned on audio
    Wav2Lip-->>Pipe: Return raw lip-synced video
    Pipe->>GFPGAN: Apply sub-nasal mask + GFPGAN super-resolution
    GFPGAN-->>Pipe: Return final restored frames with untouched upper face
    end

    Pipe->>Web: Output final dubbed MP4 file
    Web-->>User: Display video in web player with synchronized audio
```

---

## 3. Sub-Nasal Selective Compositing Topology

```mermaid
flowchart LR
    SourceFrame["Original Camera Frame (1080p)"] --> FaceMesh["MediaPipe 468 3D Face Mesh"]
    FaceMesh --> Anchor["Sub-Nasal Anchor (Point 2) & Mouth Corners (61, 291)"]
    Anchor --> DynamicMask["Dynamic Sub-Nasal Elliptical Mask"]
    
    Wav2LipFrame["Wav2Lip 96x96 Generated Mouth"] --> GFPGANNet["GFPGAN v1.4 Neural Restorer"]
    GFPGANNet --> RestoredMouth["Crisp Teeth, Lips & Skin Texture"]
    
    SourceFrame & RestoredMouth & DynamicMask --> AlphaBlend["Gaussian Feathering (σ=5) Alpha Compositor"]
    AlphaBlend --> FinalCrispFrame["Finished Frame<br/>(100% Untouched Eyes, Face & Background)"]
```
