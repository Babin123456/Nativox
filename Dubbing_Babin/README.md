# Nativox Dubbing_Babin - Natural Actor Voice Dubbing

Cinematic-quality video dubbing that preserves the original speaker's voice timbre, pitch, emotions, and speaking rhythm while translating into the target language naturally.

## What makes this different

| Feature | Old approach | New approach |
|---------|-------------|--------------|
| Translation | Keyword extraction -> sentence reconstruction | Direct natural sentence translation (Google Translate) |
| Voice source | XTTS v2 on raw mixed audio | XTTS v2 on Demucs-separated clean vocals |
| Duration control | Single global time-stretch | Speed-loop re-generation + WSOLA precision stretch |
| Timbre matching | Basic EQ | Spectral envelope EQ + RMS loudness matching |
| Background audio | Mixed into TTS ref | Separated clean; mixed back untouched after synthesis |
| Language support | hi, en | hi, bn, en, es, fr, de, ja, ko, ru, it, pt, pl, tr, nl, cs, ar, hu, zh-cn |

## Pipeline stages

```
[01] Audio demux              FFmpeg WAV @ 44100 Hz
[02a] Transcription           faster-whisper base (CPU, int8) with word timestamps
[02b] Vocal separation        Demucs htdemucs_ft -> vocals.wav + background.wav
[02c] Reference clip          Best 10s voiced segment from vocals stem
[03] Natural translation      Google gtx REST -> deep-translator fallback + cadence check
[04] XTTS v2 synthesis        N=3 candidates per chunk, best wins by MFCC/pitch score
                              Speed-loop re-generation if >10% off target duration
                              WSOLA time-stretch for final precision alignment
[05] Post-processing          Spectral EQ (formant proxy) + RMS loudness matching
[06] Background mix           Separated background mixed back at original levels
[07] Video remux              FFmpeg copy video stream, replace audio
```

## Quick start

### CLI (single command)

```bash
cd Dubbing_Babin
venv\Scripts\python pipeline.py --video path\to\video.mp4 --target-lang hi
```

### Web UI

```bash
cd Dubbing_Babin
venv\Scripts\python server.py
# Open: http://127.0.0.1:8000
```

### Supported target languages

| Code | Language |
|------|---------|
| hi | Hindi |
| bn | Bengali |
| en | English |
| es | Spanish |
| fr | French |
| de | German |
| ja | Japanese |
| ko | Korean |
| ru | Russian |
| it | Italian |
| pt | Portuguese |
| pl | Polish |
| tr | Turkish |
| nl | Dutch |
| cs | Czech |
| ar | Arabic |
| hu | Hungarian |
| zh-cn | Chinese (Mandarin) |

> Note: Bengali text is routed through Hindi phonetics in XTTS v2 since XTTS does not natively support the Bengali script.

## Output files

All outputs are written to `outputs/<job_id>/`:

| File | Description |
|------|-------------|
| `final_dubbed_video.mp4` | Final dubbed video (ready to watch) |
| `dubbed_audio.wav` | Dubbed voice + original background mix (stereo, 44100 Hz) |
| `cloned_voice_only.wav` | XTTS v2 output before background mix |
| `voice_profile_vocals.wav` | Demucs vocals stem |
| `voice_profile_background.wav` | Demucs background stem |
| `voice_profile_clips/clip_01.wav` | Reference clip used for XTTS voice embedding |
| `voice_latents.pt` | Cached XTTS voice embedding (speeds up re-runs) |
| `transcript.txt` | Original speech transcript |
| `dubbed_text.txt` | Translated text used for synthesis |
| `segments.json` | Whisper segments with timestamps |
| `audio.wav` | Demuxed audio track |

## Requirements

Install inside the venv:

```bash
venv\Scripts\pip install -r requirements.txt
```

Key packages:
- `coqui-tts>=0.22.0` - XTTS v2 multilingual voice cloning
- `demucs` - Neural vocal/background separation
- `faster-whisper` - Fast Whisper transcription
- `librosa>=0.10.0` - Audio processing and WSOLA time-stretch
- `deep-translator` - Fallback translation
- `soundfile` - WAV/FLAC audio I/O
- `scipy` - Signal processing (IIR filters)

## Module reference

| File | Role |
|------|------|
| `pipeline.py` | Main orchestrator; runs all 7 stages end-to-end |
| `audio_processor.py` | Demucs separation, pitch profiling, time-stretch, EQ, loudness |
| `translator.py` | Natural sentence translation with cadence check |
| `voice_synthesizer.py` | XTTS v2 loading, embedding, chunk synthesis, post-processing |
| `cloner.py` | Legacy XTTS v2 runner (kept as fallback) |
| `server.py` | FastAPI web server and REST API |
| `web/index.html` | Web UI dashboard |

## Notes

- XTTS v2 downloads ~1.8 GB on first run (cached in `~\.local\share\tts\`)
- Demucs `htdemucs_ft` downloads ~300 MB on first run (cached in `~\.cache\torch\`)
- CPU inference is slower but produces the same quality as GPU
- Approximate processing time on CPU: 3-5x video duration
