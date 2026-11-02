# Nativox Lipsync Analyzer

This module compares mouth-opening movement in three videos:

- `videos/real_hindi.mp4`: reference performance
- `videos/dubbed.mp4`: dubbed video before lipsync
- `videos/dubbed_lipsync.mp4`: dubbed video after lipsync

The analyzer uses MediaPipe Face Mesh to measure normalized lip opening per
frame, aligns curves, calculates correlation, and saves a graph in `output/`.

## Run on Windows

1. Put the three videos in `videos/` (or upload them in the web interface).
2. Double-click `run.bat`.
3. Open <http://127.0.0.1:8020>.

The first run creates `backend/venv/` and installs the dependencies. The API is
also available at `/docs`.

## API

`POST /api/analyze` accepts multipart fields `real_hindi`, `dubbed`, and
`dubbed_lipsync`. It returns correlation scores, frame counts, and a URL for
the generated mouth-curve graph.
