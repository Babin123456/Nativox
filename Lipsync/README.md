# Lipsync: Lip-Sync Evaluation

Compares mouth movement in a real Hindi recording with dubbed videos, with
and without Wav2Lip.

## Run

Double-click `run.bat`, then open <http://127.0.0.1:8001>.

## How it works

1. Detect a face and measure mouth opening in every frame.
2. Resample all videos to a common timeline and normalize mouth size.
3. Find the delay, then compare the mouth curves with correlation and DTW.
4. Generate a comparison graph and optional FFmpeg side-by-side video.

## Requirements

Use Python 3.11, FFmpeg on `PATH`, and a clear front-facing face in each
video. The first run creates `backend/venv` and installs dependencies.
