# Nativox Lip-Sync Evaluation Suite

A quantitative audiovisual lip-synchronization and mouth motion evaluation tool. It extracts facial landmarks frame-by-frame, generates normalized vertical mouth opening curves (Mouth Aspect Ratio / aperture), aligns timelines, and measures statistical correlation and Dynamic Time Warping (DTW) distance against a ground-truth reference video.

---

## 📋 System Prerequisites

Ensure the following dependencies are installed and available on your system environment:

- **Python:** 3.11 (strictly pinned repository-wide via `.python-version`)
- **FFmpeg:** Installed and available on system `PATH` (used for video decoding and side-by-side rendering)
- **Git** (for repository clone/submodule management)

---

## 🛠️ Installation & Setup

All commands should be executed from within the `Lipsync` directory.

### 1. Navigate to the Service Directory

```bash
cd Lipsync
```

### 2. Configure Virtual Environment

#### On Windows (PowerShell / Command Prompt)

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
```

#### On Linux / macOS (Bash / Zsh)

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🚀 Running the Application

### Start the FastAPI Server

Run the application server using `uvicorn`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Once the server has initialized, navigate to:
👉 **[http://127.0.0.1:8001](http://127.0.0.1:8001)**

---

## 🧪 How It Works

1. **Facial Landmark & Aperture Extraction:** Uses MediaPipe Face Mesh / OpenCV to detect lip contours and compute vertical mouth opening metrics across each video frame.
2. **Timeline Normalization & Interpolation:** Resamples video sequences to a synchronized temporal baseline and normalizes mouth aperture against overall facial dimensions.
3. **Temporal Delay & Cross-Correlation:** Computes lag offset ($\tau^*$) via cross-correlation and measures shape similarity with Dynamic Time Warping (DTW).
4. **Visual & Statistical Output:**
   - **Metrics Table:** Pearson correlation coefficient ($r$), DTW alignment score, mean squared error, and audio/video delay in milliseconds ($\text{ms}$).
   - **Mouth Movement Graph:** Comparative temporal plot comparing aperture traces across candidates.
   - **Side-by-Side Video:** Automated FFmpeg side-by-side composition previewing synchronous playback.

---

## 📡 API Reference

### Health Check / Web UI

- **Endpoint:** `GET /`
- **Description:** Serves the interactive web interface.

### Run Comparison

- **Endpoint:** `POST /api/compare`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `real` *(File, required)*: Ground-truth reference video (e.g., native Hindi speaker).
  - `dubbed` *(File, required)*: Dubbed video without neural lip modification (baseline).
  - `lipsync` *(File, optional)*: Neural-dubbed video (e.g., Wav2Lip / VideoReTalking).
- **Response Format:**

  ```json
  {
    "results": {
      "Dubbed (no lip-sync)": {
        "correlation": 0.42,
        "dtw_correlation": 0.51,
        "error": 0.082,
        "delay_ms": 120
      },
      "Dubbed + Wav2Lip": {
        "correlation": 0.78,
        "dtw_correlation": 0.83,
        "error": 0.031,
        "delay_ms": 15
      }
    },
    "plot": "/output/compare_plot.png",
    "video": "/output/side_by_side.mp4"
  }
  ```

---

## 📂 Directory Structure

```text
Lipsync/
├── backend/
│   ├── app/
│   │   ├── compare.py        # Temporal alignment, DTW, & scoring logic
│   │   ├── mouth_curve.py    # MediaPipe landmark extraction & mouth curves
│   │   └── plot.py           # Matplotlib curve comparison generator
│   ├── main.py               # FastAPI server application
│   └── requirements.txt      # Python dependencies
├── frontend/
│   └── index.html            # Evaluation dashboard UI
├── output/                   # Generated evaluation plots and side-by-side videos
├── videos/                   # Upload storage cache
└── README.md                 # Service documentation
```
