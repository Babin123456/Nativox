# Nativox Universal Dub & LipSync Studio

A unified, end-to-end pipeline and interactive Web UI.  
You provide **ONLY ONE input video**, and the pipeline executes:
1. **Stage 00 Dubbing Pipeline:** Audio extraction, transcription, voice profile analysis, keyword extraction, sentence construction, Hindi translation, and natural speech synthesis (`dubbed_audio.wav`).
2. **Selective LipSync Engine:** Takes the input video and newly dubbed audio, runs Wav2Lip GAN neural mouth synthesis, and applies MediaPipe 468-point sub-nasal landmark tracking with feather blending.
3. **Pristine Output:** Only the mouth and jaw are articulated. The background, eyes, eyebrows, nose, forehead, hair, and camera lighting remain **100% original camera pixels**.

---

## 1. Prerequisites

1. **Python 3.10 or 3.11**
2. **FFmpeg** installed and accessible from system PATH (`ffmpeg -version`).
3. **Model Weights:**  
   - Wav2Lip GAN checkpoint: `LipSync_Babin/models/wav2lip/checkpoints/wav2lip_gan.pth`
   - SFD Face detector checkpoint: `LipSync_Babin/models/wav2lip/face_detection/detection/sfd/s3fd.pth`  
   *(Both are already present in the workspace).*

---

## 2. Setup & Installation

Navigate into the `Dub_with_LipSync` folder:

```bash
cd d:\Projects\Nativox\Dub_with_LipSync
```

### 2. Virtual Environment Setup & Activation

Create and activate a dedicated virtual environment inside this folder:

- **Create Environment (First Time Only):**
  ```bash
  python -m venv venv
  ```

- **Activate Environment:**
  - **Windows PowerShell:**
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
  - **Windows Command Prompt:**
    ```cmd
    .\venv\Scripts\activate.bat
    ```
  - **Linux / macOS:**
    ```bash
    source venv/bin/activate
    ```

- **Install Dependencies:**
  ```bash
  pip install -r requirements.txt
  ```

---

## 3. Running the Studio (Single Pure Python Command)

From inside the `Dub_with_LipSync` directory:

```bash
python app.py
```

*(Or direct execution via the local virtual environment: `.\venv\Scripts\python.exe app.py`)*

### What happens automatically:
1. Starts the server at `http://127.0.0.1:8080`.
2. Automatically launches your default web browser to the studio interface.

---

## 4. How to Use

1. **Upload Input Video:** Drag and drop your original video (`.mp4`, `.mov`, `.mkv`, etc.).
2. **Click Start:** Press **Start Dubbing & Lip-Sync Pipeline**.
3. **Automatic End-to-End Processing:**
   - **Stage 1 (Dubbing):** Transcribes speech, extracts keywords, constructs sentences, translates to Hindi, and synthesizes natural speech.
   - **Stage 2 (LipSync):** Articulates lips strictly below the philtrum line onto the original camera video.
4. **View & Download:** Watch the real-time logs in the browser, compare original vs. final video side-by-side, and click **Download Final Video**.

---

## 5. File Structure

```
Dub_with_LipSync/
├── app.py                # Unified FastAPI orchestrator (Stage 00 Dubbing + LipSync)
├── run_dub_lipsync.py    # Wav2Lip + sub-nasal selective compositor pipeline
├── requirements.txt      # Python dependencies
├── README.md             # Complete documentation
├── frontend/
│   └── index.html        # Single-input-video modern dark-mode Web UI
├── jobs/                 # Intermediate runtime job directories (scratch & staging)
└── outputs/              # Primary storage for all final dubbed & lip-synced videos
```
