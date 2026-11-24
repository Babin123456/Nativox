<!-- markdownlint-disable -->

# Nativox LipSync_Babin: Zero-API Multilingual Video Dubbing & High-Definition Lip Sync

> **Autonomous AI Video Dubbing**: Dub any talking-head English video into natural **Hindi (`hi`)** and **Bengali (`bn`)** with **1:1 Video Duration Synchronization**, **Continuous Background Music Preservation**, **Speaker Vocal Timbre/Pitch Cloning**, and **High-Definition Lip Sync** (GFPGAN + MediaPipe Sub-Nasal Compositing)—**100% Free with ZERO API Keys required**.  
> **Creator & Lead Architect**: Babin Bid  

---

## 🌟 Key Features

1. **100% Free / Zero API Key Architecture**: Runs completely on your machine. No API keys, paid credits, or third-party service subscriptions are needed.
2. **Interactive Web Dashboard**: Upload any video directly in your browser, pick target language, and preview the translated, voice-cloned, lip-synced video instantly.
3. **True Speaker Voice Identity Transfer**: Clones and preserves the original speaker's vocal pitch, throat resonance, and speaking timbre across languages.
4. **Continuous Background Music Preservation**: Extracts and preserves original background audio/music, seamlessly remuxing it with the dubbed speech.
5. **High-Definition Sub-Nasal Lip Sync**: Powered by Wav2Lip + GFPGAN v1.4 restoration + 468 MediaPipe facial landmarks, keeping eyes, nose, hair, and scene lighting 100% untouched original pixels.

---

## 🚀 Quick Start (Web UI)

The primary and simplest way to use LipSync_Babin is via the interactive **Web UI**. You do not need to prepare test folders—simply upload your video through the browser interface.

### 1. One-Time Setup

Open PowerShell or Terminal in the `LipSync_Babin` directory:

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Download neural weights (Wav2Lip GAN, GFPGAN v1.4, Face Detector)
python setup_models.py
```

> **Tip**: If you already have `Dub_with_LipSync\venv` configured on your system, you can skip creating a new `.venv` and run `app.py` directly using that Python executable.

---

### 2. Launch the Web UI

Simply navigate into the `web` folder and run `app.py`:

```powershell
cd web
python app.py
```

Once running, open your browser at:
👉 **`http://127.0.0.1:7860`**

### Using the Web UI:
1. **Upload Video**: Drag and drop any talking-head `.mp4` video directly into the drop zone.
2. **Select Language**: Choose **Hindi** or **Bengali**.
3. **Voice Mode**: Default is **Zero-API Mode (100% Free / No Keys)**.
4. **Click "Dub Video Now"**: The system transcribes, translates, clones the speaker's voice, articulates lips with GFPGAN restoration, and streams the finished video in the player.

---

## 💻 Optional: Command-Line Interface (Demo / Batch)

If you prefer testing via terminal with an attached demo video (such as `test2.mp4` included in the root directory):

```powershell
# Dub attached demo video to Hindi:
python pipeline.py --input test2.mp4 --lang hi --tts free --preserve-bgm --output outputs/demo_hindi_dubbed.mp4

# Dub attached demo video to Bengali:
python pipeline.py --input test2.mp4 --lang bn --tts free --preserve-bgm --output outputs/demo_bengali_dubbed.mp4
```

### CLI Options:
| Flag | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input` | File path (`.mp4`) | *Required* | Path to your demo or test video file |
| `--lang` | `hi`, `bn` | *Required* | Target language (`hi` = Hindi, `bn` = Bengali) |
| `--output` | File path (`.mp4`) | *Required* | Destination path for the final dubbed video |
| `--tts` | `free`, `edgetts`, `sarvam` | `free` | Speech synthesis engine (`free` requires 0 keys) |
| `--preserve-bgm`| Flag | `True` | Preserves and mixes original background music |
| `--enhance` | Flag | `True` | Restores teeth/lips sharpness with GFPGAN v1.4 |

---

## 🛠️ Common Notes

- **Port in Use?** You can launch on another port with `python -m uvicorn app:app --port 7865`.
- **MediaPipe Version**: For optimal landmark support, keep `mediapipe<0.10.30`.
- **Rendered Outputs**: Final videos generated via the Web UI are automatically stored in the `outputs/` folder.

---

## 📁 Repository Directory Structure

```
LipSync_Babin/
├── README.md                  # Master guide (Web UI & setup)
├── ARCHITECTURE.md            # System architecture & pipeline diagrams
├── INSTRUCTIONS.md            # Technical specifications & working principles
├── MATHEMATICAL_FOUNDATIONS.md# Acoustic and alignment mathematics
├── setup_models.py            # Neural model weight downloader
├── pipeline.py                # Core pipeline orchestration engine
├── requirements.txt           # Python package dependencies
├── test2.mp4                  # Sample demo video file
│
├── web/                       # Web Dashboard Interface
│   ├── app.py                 # Main Web UI server (run with: cd web && python app.py)
│   └── templates/index.html   # Responsive web interface
│
├── lipsync/                   # Neural mouth sync & GFPGAN super-resolution
├── synthesis/                 # Zero-API neural TTS and voice identity morphing
├── translation/               # Colloquial translation & syllable budgeting
├── speech_analysis/           # Vocal pitch, formant, and prosody transfer
├── utils/                     # BGM separation (HTDemucs) & audio/video tools
└── outputs/                   # Destination for processed dubbed videos
```
