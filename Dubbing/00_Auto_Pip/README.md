<!-- markdownlint-disable -->

# Nativox Automatic Pipeline (`00_Auto_Pip`)

`00_Auto_Pip` runs the complete Nativox video-dubbing workflow from a single command. It orchestrates all stages into an end-to-end automated dubbing pipeline:

```text
Input Video (.mp4)
  -> [01] MP3 Audio Extracted
  -> [02] Parallel Execution:
         * [2a] Speech-to-Text Transcription & VAD (Whisper)
         * [2b] Speaker Voice Extraction & Profiling (Stage 08 main.py)
  -> [03] Salient Keyword Extraction (RAKE) [TEMPORARILY SKIPPED BY DEFAULT]
  -> [04] Neural Sentence Construction (Flan-T5) [TEMPORARILY SKIPPED BY DEFAULT]
  -> [05b] Hindi Sentence Reformation & Vernacular Translation (Direct Transcript Mode)
  -> [06] Author Voice Cloning & Synthesis (Stage 08 test_cloned.py, XTTS v2)
  -> [07] Dubbed Audio Video Remuxing (Zero Truncation)
  -> Output Dubbed Video (final_dubbed_video.mp4)
```

> [!IMPORTANT]
> **Stage 3 and 4 are temporarily skipped:** By default, Stage 03 (Keyword Extraction) and Stage 04 (Sentence Construction) are temporarily skipped in `00_Auto_Pip`. The pipeline routes the high-fidelity speech transcript from Stage 02 directly into Stage 05b for vernacular reformation and translation, preserving complete dialogue fluency and accelerating processing. You can re-enable them at any time whenever needed.

> **Note on Stage 05(a):** Stage 05(a) (`05a_Keyword_Translation__Sagnik`) remains available as a standalone research module in the repository. The automated dubbing pipeline directly routes Stage 04 reconstructed sentences into Stage 05(b) for vernacular translation and disfluency reformation.

---

## 🔄 How to Enable Stages 3 and 4

If you want to re-enable Stage 03 (Keyword Extraction) and Stage 04 (Sentence Construction), you can do so easily through any of the following methods:

### Method 1: Web Dashboard (One-Click Toggle)
In the interactive Web UI (`http://127.0.0.1:8000`):
1. Locate the switch above the execution button labeled:  
   **"Skip Stage 3 (Keywords) & Stage 4 (Sentence Construction)"**
2. **Toggle the switch OFF (Unchecked)** to re-enable Stage 03 & Stage 04.
3. Click **"Execute Full End-to-End Dubbing Pipeline"** to run all 8 stages.

### Method 2: CLI Command Flag
When executing `orchestrator.py` from your terminal, pass `--enable-stages-3-4`:

```bash
# Re-enable Stages 3 & 4 (Full 8-stage execution):
python orchestrator.py "path/to/video.mp4" --enable-stages-3-4

# Default run (Stages 3 & 4 temporarily skipped):
python orchestrator.py "path/to/video.mp4"

# Explicitly skip Stages 3 & 4:
python orchestrator.py "path/to/video.mp4" --skip-stages-3-4
```

### Method 3: Environment Variable
Set the `NATIVOX_SKIP_STAGES_3_4` environment variable before running:

- **Windows PowerShell:**
  ```powershell
  $env:NATIVOX_SKIP_STAGES_3_4="0"  # 0 = Enabled (Run stages 3 & 4)
  $env:NATIVOX_SKIP_STAGES_3_4="1"  # 1 = Skipped (Default bypass)
  ```
- **Linux / macOS:**
  ```bash
  export NATIVOX_SKIP_STAGES_3_4="0"  # 0 = Enabled (Run stages 3 & 4)
  export NATIVOX_SKIP_STAGES_3_4="1"  # 1 = Skipped (Default bypass)
  ```

### Method 4: Code Configuration
You can also change the default in the source files directly:
- In `orchestrator.py`: change `SKIP_STAGES_3_AND_4 = True` to `SKIP_STAGES_3_AND_4 = False`.
- In `main.py`: change `SKIP_STAGES_3_AND_4 = True` to `SKIP_STAGES_3_AND_4 = False`.

---

## 📋 Requirements

- **Python:** 3.11 (Pinned repository-wide via `.python-version`)
- **FFmpeg:** Installed and available on system `PATH` (required by Stages 01 and 07)
- **Input:** Source video file (`.mp4`, `.mov`, `.mkv`, etc.)

---

## 🚀 Environment Setup

All commands are run directly from inside `Dubbing/00_Auto_Pip/`:

```bash
cd Dubbing/00_Auto_Pip
```

Install all stage dependencies across the repository using the setup utility:

```bash
# Using active Python environment
python setup_env.py

# Or create and install into dedicated 00_Auto_Pip/venv
python setup_env.py --create-venv
```

Activate the virtual environment when needed:
- **Windows:** `.\venv\Scripts\activate`
- **Linux / macOS:** `source venv/bin/activate`

---

## 🖥️ Running the Interactive Web UI

From `Dubbing/00_Auto_Pip/`:

```bash
# Start Web UI and auto-launch all background microservices
python main.py --auto-start
```

> **Tip:** The `--auto-start` flag causes `main.py` to automatically detect and launch any missing backend microservice stages in the background, eliminating the need to start each stage manually!

*Or run the web server without auto-starting background stages:*

```bash
python main.py
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

### Dashboard Features

- **Service Health Monitor:** Live status pings for all backend microservices (`8001`–`8008`).
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
# Default (Stages 3 & 4 temporarily skipped):
python orchestrator.py "path/to/video.mp4"

# Re-enable Stages 3 & 4 (Full 8-stage pipeline):
python orchestrator.py "path/to/video.mp4" --enable-stages-3-4

# Explicitly skip Stages 3 & 4:
python orchestrator.py "path/to/video.mp4" --skip-stages-3-4
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
| **05b** | Sentence Reformation & Précis | `8005` | `/api/health` |
| **06** | Converted Text to MP3 (Edge TTS) | `8006` | `/api/health` |
| **07** | Final Video & Audio Merge | `8007` | `/api/health` |
| **08** | Acoustic Profiling & Voice Cloning (XTTS v2) | CLI / `8008` | Direct CLI / In-Process |


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
- **Port already in use:** Verify another process is not binding to ports `8001`–`8008` or run `python orchestrator.py --status`.
- **FFmpeg not found:** Ensure `ffmpeg` is installed and added to `PATH` (`ffmpeg -version`).
- **Coqui TTS & Voice Cloning (`TTS` / `demucs`):** Stages 2b and 06 use Demucs and Coqui XTTS v2 for background separation and cloned voice synthesis. Ensure `coqui-tts`, `demucs`, and `torchaudio` are installed in your environment (`pip install -r requirements.txt`).
- **Stage 4 PyTorch Security Warning:** If Windows Application Control blocks `c10.dll`, ensure Python is installed in an approved user directory.
