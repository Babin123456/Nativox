# Dubbing_Babin — Streamlined AI Video Dubbing Studio

A high-performance, single-command video dubbing pipeline for **Nativox**. 

`Dubbing_Babin` isolates and runs **strictly the essential production stages** (`[01 Demux -> 02a Faster-Whisper -> 02b Demucs Profiling -> Direct Translation -> 06 XTTS v2 Cloner -> 07 Zero-Truncation Remux]`), skipping intermediate research stages (Keywords, T5 Sentence Reconstruction, Disfluency Précis).

---

## Architecture: The Core Production Pipeline

```text
[Input Video (.mp4 / .mov / .mkv)]
       │
       ▼
[01] Audio Demuxing (FFmpeg)
       │  • Extracts audio.mp3 and detects exact video duration
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[02a] Faster-Whisper               [02b] Speaker Profiling (Demucs)
      • Neural Speech-to-Text            • Separates vocals & background audio
      • Exact word-level timestamps      • Extracts clean acoustic reference clips
      • Spoken dialogue window locked    • Generates voice profile & timbre map
       │                                 │
       ▼                                 │
[Translation] Direct Vernacular          │
      • Multi-tiered Google GTX client   │
      • Rate-limit proof with backoff    │
      • Generates dubbed_text.txt        │
       │                                 │
       └────────────────┬────────────────┘
                        ▼
[06] Author Voice Cloning & Synthesis (XTTS v2 + Cloner)
      • Enhanced emotive temperature (T=0.80) & tone matching (EQ 0.70)
      • Phase-vocoder time-stretch to match exact spoken dialogue window
      • Restores untouched original background audio
      • Generates dubbed_audio.mp3
                        │
                        ▼
[07] Remuxing & Video Merging (FFmpeg)
      • Zero video frame truncation
      • Guarantees 100% video frame & audio timeline alignment
                        │
                        ▼
[final_dubbed_video.mp4]
```

---

## 📋 Prerequisites & Setup

### 1. Requirements
- **Python:** `3.11` (strictly recommended for PyTorch, Coqui TTS, and CTranslate2)
- **FFmpeg:** Installed and added to system `PATH` (`ffmpeg -version`)

### 2. Virtual Environment Setup
From repository root or `Dubbing_Babin`:

```bash
cd Dubbing_Babin

# Create local virtual environment
python -m venv venv

# Activate on Windows:
.\venv\Scripts\activate

# Activate on Linux / macOS:
source venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

## 🖥️ Running the Interactive Web Studio

Launch the modern dark-mode SaaS Web Dashboard from inside `Dubbing_Babin`:

```bash
cd Dubbing_Babin
python server.py
```

*Or run on a custom port:*
```bash
python server.py --port 8080
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

### Dashboard Features:
- **Drag-and-Drop Media Upload:** MP4, MOV, or MKV containers.
- **Target Vernacular Picker:** Dub into Hindi (`hi`), Spanish (`es`), French (`fr`), German (`de`), Japanese (`ja`), Russian (`ru`), and more.
- **Live Stage Stepper:** Visual step tracking across all 6 production stages.
- **Streaming Telemetry Terminal:** Real-time Whisper logs, translation metrics, and voice cloning status.
- **Side-by-Side Synchronized Studio Player:** Direct preview of the original video against the finalized dubbed video with audio playback.
- **Instant Download:** One-click download for `final_dubbed_video.mp4`.

---

## ⚡ Running via CLI (Single Command)

All execution happens directly inside `Dubbing_Babin`:

```bash
cd Dubbing_Babin

# Basic command (Dub to Hindi)
python pipeline.py --video "path/to/video.mp4" --target-lang hi
```

### Examples:
```bash
# Dub a video to Spanish:
python pipeline.py --video "D:/Videos/speech.mp4" --target-lang es

# Dub a video and specify custom output folder:
python pipeline.py --video "D:/Videos/speech.mp4" --target-lang hi --work-dir "outputs/my_job"
```

### CLI Options:
| Flag | Short | Default | Description |
| :--- | :---: | :---: | :--- |
| `--video` | `-v` | *Required* | Path to input talking-head video file (`.mp4`, `.mov`, `.mkv`). |
| `--target-lang` | `-l` | `hi` | Target language code (`hi`, `es`, `fr`, `de`, `it`, `pt`, `ru`, `ja`, `zh-cn`). |
| `--work-dir` | `-o` | `outputs/job_<timestamp>` | Destination folder for intermediate and final outputs. |

---

## ⚙️ Voice Expression & Timing Alignment Details

- **Dialogue Window Locking:** Instead of stretching speech across silent pauses or trailing scenes, the pipeline locks dialogue synthesis strictly to the speaker's active speaking timestamps.
- **Phase-Vocoder Alignment:** If the translated text naturally requires more or fewer syllables, `cloner.py` applies a phase-vocoder time-stretch to fit the speaking duration without pitch or timbre distortion.
- **Emotive Expression:** `cloner.py` operates at `T=0.80` with a 3-candidate pitch-contour selection to capture vocal emotion, inflection, and natural conversational cadence.
- **Tone & Brightness Equalization:** High-frequency rasp and vocal presence are restored via spectral tilt matching (`EQ_STRENGTH = 0.70`).

---

## 📦 Generated Output Artifacts

Each run saves clean, structured outputs in `outputs/job_<id>/`:

| File | Description |
| :--- | :--- |
| `audio.mp3` | Isolated audio track extracted from the input video. |
| `transcript.txt` | Clean timestamped transcription from Faster-Whisper. |
| `voice_profile.json` | Acoustic metrics ($F_0$ pitch median, timbre MFCC, energy envelope). |
| `voice_profile_clips/` | Isolated reference clips for speaker voice conditioning. |
| `dubbed_text.txt` | Target language translated dialogue script. |
| `cloned_voice_only.wav` | Isolated synthesized voice clone track. |
| `dubbed_audio.mp3` | Final dubbed audio with preserved background sounds. |
| `final_dubbed_video.mp4` | Final output video with 100% video frame preservation and synchronized audio. |
