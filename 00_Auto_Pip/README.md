# Nativox Automatic Pipeline (`00_Auto_Pip`)

`00_Auto_Pip` runs the complete Nativox video-dubbing workflow from a single command. It orchestrates all stages into an end-to-end automated dubbing pipeline:

```text
Input Video (.mp4)
  -> [01] MP3 Audio Extracted & Speaker Pitch Analyzed
  -> [02] Speech-to-Text Transcription & VAD (Whisper)
  -> [03] Salient Keyword Extraction (RAKE)
  -> [04] Neural Sentence Construction (Flan-T5)
  -> [05b] Hindi Sentence Reformation & Vernacular Translation
  -> [06] Neural Speech Synthesis (Edge Neural TTS, Voice Gender Matched)
  -> [07] Dubbed Audio Video Remuxing (Zero Truncation)
  -> Output Dubbed Video (final_dubbed_video.mp4)
```

> **Note on Stage 05(a):** Stage 05(a) (`05a_Keyword_Translation__Sagnik`) remains available as a standalone research module in the repository. The automated dubbing pipeline directly routes Stage 04 reconstructed sentences into Stage 05(b) for vernacular translation and disfluency reformation.

---

## 📋 Requirements

- **Python:** 3.11 (Pinned repository-wide via `.python-version`)
- **FFmpeg:** Installed and available on system `PATH` (required by Stages 01 and 07)
- **Input:** Source video file (`.mp4`, `.mov`, `.mkv`, etc.)

---

## 🚀 Environment Setup

Install all stage dependencies across the repository using the cross-platform setup utility:

```bash
cd 00_Auto_Pip
python setup_env.py
```

To create and use a dedicated virtual environment in `00_Auto_Pip/venv`:

```bash
python setup_env.py --create-venv
```

---

## 🖥️ Running the Interactive Web UI

`00_Auto_Pip` provides a dedicated web dashboard running on port `8000` that connects all 8 microservices, monitors service health, and manages video dubbing with live progress tracking and side-by-side video playback:

```bash
cd 00_Auto_Pip
python main.py
```

*Or using uvicorn with hot-reload:*
```bash
cd 00_Auto_Pip
uvicorn main:app --reload --port 8000
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

### Dashboard Features:
- **Service Health Monitor:** Live status pings for all 8 backend microservices (`8001`–`8014`).
- **Drag & Drop Upload:** Accepts any standard video file (`.mp4`, `.mov`, `.mkv`, etc.).
- **Live Multi-Stage Stepper:** Visual tracking of active stages from demuxing to remuxing.
- **Real-Time Terminal Output:** Displays pitch analysis, dynamic speech pacing rate, and step logs.
- **Side-by-Side Comparison Player:** Synchronized preview of original video vs final dubbed video.
- **One-Click Artifact Downloads:** Instant downloads for all intermediate files and the final MP4.

---

## 🎙️ Automatic Voice Gender Detection & Matching

The pipeline automatically analyzes the acoustic profile of the speaker in the uploaded video to match their gender in the dubbed output:

1. **Acoustic Fundamental Frequency ($F_0$ Pitch) Analysis:**
   - Evaluates periodic harmonic autocorrelation across voiced frames in the extracted audio.
   - Adult Male Voices: Typically **85 Hz – 165 Hz** (average ~110–130 Hz).
   - Adult Female Voices: Typically **165 Hz – 265 Hz** (average ~200–220 Hz).
2. **Dynamic Neural Voice Assignment:**
   - **Male Speaker Detected:** Synthesizes with **`hi-IN-MadhurNeural`** (Hindi) / **`bn-IN-BashkarNeural`** (Bengali).
   - **Female Speaker Detected:** Synthesizes with **`hi-IN-SwaraNeural`** (Hindi) / **`bn-IN-TanishaaNeural`** (Bengali).

---

## ⏱️ Video Duration Preservation & Pacing

- **Zero Truncation Remuxing:** Stage 07 avoids `-shortest` cutoff by padding speech with silence (`-af apad`) and strictly capping to original video duration (`-t <video_duration>`), guaranteeing 100% video frame preservation.
- **Full Dialogue Dubbing:** Defaults to complete dialogue translation (`step1_meaningful_hindi`) rather than 35% précis compression, ensuring continuous speech coverage across the video.
- **Dynamic Speech Pacing:** Automatically calculates speech pacing rate (`tts_rate` e.g. `-9%`) to align speech delivery across 85%–92% of the video duration.

---

## ⚡ Running the Pipeline via CLI

Run the orchestrator with your input video. It automatically starts any missing stage services, executes the workflow in order, and stops only the services it started:

```bash
python orchestrator.py "path/to/video.mp4"
```

### Custom Output Directory

By default, outputs are saved to `jobs/job1`. Specify a custom folder via `--work-dir`:

```bash
python orchestrator.py "path/to/video.mp4" --work-dir "path/to/output_folder"
```

### Using Existing Running Services

If services are already running manually or on external ports, prevent automatic service management:

```bash
python orchestrator.py "path/to/video.mp4" --no-auto-start
```

---

## 🔍 Service Health & Management

Check the health and reachability of all stage microservices:

```bash
python orchestrator.py --status
```

Pre-launch all HTTP microservices in the background:

```bash
python orchestrator.py --start-services
```

---

## 🌐 HTTP Microservice Architecture & Ports

| Stage | Module Name | Port | Health Endpoint |
| :---: | :--- | :---: | :--- |
| **01** | MP4 to MP3 Audio Extractor | `8001` | `/health` |
| **02** | Speech-to-Text Transcription (Whisper) | `8002` | `/api/languages` |
| **03** | Salient Keyword Extraction (RAKE) | `8003` | `/api/health` |
| **04** | Sentence Construction (Flan-T5) | `8004` | `/api/health` *(or in-process)* |
| **05a** | Keyword Translation & Phonetics | `8011` | `/api/health` |
| **05b** | Sentence Reformation & Précis | `8012` | `/api/health` |
| **06** | Converted Text to MP3 (Edge TTS) | `8013` | `/api/health` |
| **07** | Final Video & Audio Merge | `8014` | `/api/health` |

---

## 📦 Generated Output Artifacts

Each pipeline job generates the following structured outputs:

- `audio.mp3` — Pristine isolated audio from source video.
- `transcript.txt` — High-accuracy timestamped text transcript.
- `keywords.json` — Salient domain terminology in spoken sequence.
- `constructed_sentence.txt` — Reconstructed fluent sentence.
- `translated_keywords.json` — Target-language translated vocabulary.
- `reformed_text.json` — Disfluency-stripped Hindi sentence and précis data.
- `dubbed_text.txt` — Final compressed Hindi script for dubbing.
- `dubbed_audio.mp3` — Synthesized target-language neural speech.
- `final_dubbed_video.mp4` — Final video remuxed with dubbed audio.

---

## 🛠️ Troubleshooting

- **Python not recognized / wrong version:** Ensure Python 3.11 is active (`python --version`). Avoid Python 3.14+ as it lacks binary wheels for PyTorch and CTranslate2.
- **Port already in use:** Verify another process is not binding to ports `8001`–`8014` or run `python orchestrator.py --status`.
- **FFmpeg not found:** Ensure `ffmpeg` is installed and added to `PATH` (`ffmpeg -version`).
- **Stage 4 PyTorch Security Warning:** If Windows Application Control blocks `c10.dll`, ensure Python is installed in an approved user directory.
