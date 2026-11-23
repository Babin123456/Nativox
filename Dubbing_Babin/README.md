# Dubbing_Babin — Streamlined AI Video Dubbing Studio

A high-performance, single-command video dubbing pipeline for **Nativox**.

`Dubbing_Babin` isolates and runs **strictly the essential production stages** (`[01 Demux -> 02a Faster-Whisper -> 02b Demucs Profiling -> Direct Translation -> 06 Universal High-Fidelity Voice Transfer -> 07 Zero-Truncation Remux]`), skipping intermediate research stages (Keywords, T5 Sentence Reconstruction, Disfluency Précis).

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
      • Spoken dialogue window locked    • Generates voice profile & biological register
       │                                 │
       ▼                                 │
[Translation] Direct Vernacular          │
      • Multi-tiered Google GTX client   │
      • Cadence-aware précis adaptation  │
      • Generates dubbed_text.txt        │
       │                                 │
       └────────────────┬────────────────┘
                        ▼
[06] Universal High-Fidelity Voice Transfer (voice_synthesizer.py)
      • Regional Neural Phonation: Human-fluent native pronunciation (Edge-TTS)
      • Praat PSOLA Tonal Transfer: Projects speaker's F0, vocal tract & formants
      • Zero robotic vocoder artifacts or metallic phase buzz
      • Smooth timeline dialogue alignment matching original speech window
      • Restores untouched original background room ambience
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

### Dashboard Features

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

### Examples

```bash
# Dub a video to Spanish:
python pipeline.py --video "D:/Videos/speech.mp4" --target-lang es

# Dub a video and specify custom output folder:
python pipeline.py --video "D:/Videos/speech.mp4" --target-lang hi --work-dir "outputs/my_job"
```

### CLI Options

| Flag | Short | Default | Description |
| :--- | :---: | :---: | :--- |
| `--video` | `-v` | *Required* | Path to input talking-head video file (`.mp4`, `.mov`, `.mkv`). |
| `--target-lang` | `-l` | `hi` | Target language code (`hi`, `es`, `fr`, `de`, `it`, `pt`, `ru`, `ja`, `zh-cn`). |
| `--work-dir` | `-o` | `outputs/job_<timestamp>` | Destination folder for intermediate and final outputs. |

---

## ⚙️ Voice Expression & Timing Alignment Details

- **Dialogue Window Locking:** Instead of stretching speech across silent pauses or trailing scenes, the pipeline locks dialogue synthesis strictly to the speaker's active speaking timestamps ($t_{\text{start}}$ to $t_{\text{end}}$).
- **Decoupled Two-Stage Voice Architecture:**
  1. *Stage 1 (Phonation):* High-fidelity regional neural phonation produces human-quality pronunciation, natural breath pauses, and native accent fluency.
  2. *Stage 2 (Tone & Formant Transfer):* Praat PSOLA shifts the vocal tract length ($F_1, F_2, F_3$) and pitch distribution to match the biological register and timbre of the original speaker without robotic vocoder distortion.
- **Cadence & Duration Awareness:** Automatic syllable-rate balancing prevents speed rushing or sluggish speech stretching, ensuring natural human conversational tempo across all languages.
- **Untouched Room Atmosphere:** Continuous background room tone, ambient beds, and SFX separated by Meta HTDemucs are remuxed back in, preserving original production value.

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
