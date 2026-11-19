# Dubbing_Babin

A streamlined, direct video dubbing pipeline for **Nativox**. 

This pipeline contains **only the strictly required stages** to convert an input video into a target-language dubbed video with cloned voice and preserved background sound in a single command, skipping intermediate research stages (Keywords, T5 Sentence Reconstruction, Disfluency Précis).

---

## 🏗️ Architecture: Strictly Required Stages

```text
[Input Video (.mp4)]
       │
       ▼
[01] Audio Demuxing (FFmpeg)
       │  • Extracts audio.mp3 and measures duration
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
[02a] Faster-Whisper               [02b] Speaker Profiling (Stage 08)
      • Automatic STT Transcription      • Demucs background audio separation
      • Generates transcript.txt         • Extracts clean vocal reference clips
       │                                 │
       ▼                                 │
[Translation] Direct Translation         │
      • Google / Deep-Translator         │
      • Generates dubbed_text.txt        │
       │                                 │
       └────────────────┬────────────────┘
                        ▼
[06] Author Voice Cloning & Synthesis (XTTS v2)
      • Clones speaker timbre & inflection
      • Restores untouched original background audio
      • Generates dubbed_audio.mp3
                        │
                        ▼
[07] Remuxing & Video Merging (FFmpeg)
      • Zero video frame truncation
      • Matches exact video timeline
                        │
                        ▼
[final_dubbed_video.mp4]
```

---

## ⚡ Quick Start (Single Command)

All execution happens directly inside `Dubbing_Babin`:

```bash
cd Dubbing_Babin
```

### Run Dubbing on Any Video:
```bash
python pipeline.py --video "path/to/video.mp4" --target-lang hi
```

### Options:
- `--video`, `-v`: Path to input video file (`.mp4`, `.mov`, `.mkv`).
- `--target-lang`, `-l`: Target language code (e.g., `hi` for Hindi, `es` for Spanish, `fr` for French, `de` for German, etc.). Default is `hi`.
- `--work-dir`, `-o`: (Optional) Custom output directory. Defaults to `outputs/job_<timestamp>/`.

---

## 📦 Output Artifacts

Each run generates:
- `audio.mp3` — Extracted original audio.
- `transcript.txt` — Source speech transcription.
- `voice_profile.json` & `voice_profile_clips/` — Extracted speaker acoustics & clean reference clips.
- `dubbed_text.txt` — Target language translated speech text.
- `cloned_voice_only.wav` — Synthesized cloned speech without background.
- `dubbed_audio.mp3` — Cloned speech mixed with original background.
- `final_dubbed_video.mp4` — Final dubbed output video.
