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

## 🖥️ Running the Interactive Web UI

Launch the modern Web Dashboard from inside `Dubbing_Babin`:

```bash
cd Dubbing_Babin
python server.py
```

*Or specify a custom port:*
```bash
python server.py --port 8080
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

### Web UI Features:
- **Drag-and-Drop Video Uploader:** Directly upload MP4, MOV, or MKV videos.
- **Target Language Picker:** Choose Hindi, Spanish, French, German, Japanese, and more.
- **Visual Multi-Stage Stepper:** Live step tracking across Stages 1, 2a, 2b, Translate, 6, and 7.
- **Real-Time Terminal Output:** View streaming Whisper transcription and synthesis logs.
- **Side-by-Side Video Comparison Player:** Compare original video against dubbed video.
- **One-Click Video Download:** Instant download for the finalized dubbed MP4.

---

## ⚡ Running the Pipeline via CLI (Single Command)

All execution happens directly inside `Dubbing_Babin`:

```bash
cd Dubbing_Babin
python pipeline.py --video "path/to/video.mp4" --target-lang hi
```

### CLI Options:
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
