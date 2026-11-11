"""
main.py
-------
FastAPI web application for Nativox Stage 00 — Automatic Pipeline Orchestrator.
Runs on http://127.0.0.1:8000.
"""

import json
import os
import shutil
import sys
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import requests
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIR = BASE_DIR / "frontend"
JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Add 00_Auto_Pip to sys.path so we can import orchestrator
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import orchestrator

app = FastAPI(
    title="Nativox Stage 00 — Automatic Pipeline Orchestrator",
    description="Master orchestration interface executing end-to-end video dubbing across all 8 microservices.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# In-memory job tracking store
job_store: Dict[str, Dict[str, Any]] = {}


@app.get("/", response_class=HTMLResponse)
def serve_frontend() -> HTMLResponse:
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Nativox Stage 00 — Pipeline Orchestrator Online</h1>")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.webp", include_in_schema=False)
def serve_favicon():
    fav = FRONTEND_DIR / "favicon.webp"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/webp")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/api/health")
def health():
    return {"status": "ok", "stage": "00_Auto_Pip", "port": 8000}


@app.get("/api/services-status")
def get_services_status():
    """Check reachability and health of all microservices in the pipeline."""
    statuses = {}
    all_ready = True
    for stage, (rel_dir, port, health_path) in orchestrator.SERVICE_CONFIG.items():
        url = f"{orchestrator.STAGES[stage]}{health_path}"
        try:
            r = requests.get(url, timeout=2)
            online = r.ok
        except Exception:
            online = False

        if not online:
            all_ready = False

        statuses[stage] = {
            "port": port,
            "url": url,
            "online": online,
            "directory": rel_dir,
        }

    return {
        "all_ready": all_ready,
        "stages": statuses,
    }


@app.post("/api/start-services")
def start_missing_services():
    """Trigger background start of missing microservices."""
    try:
        owned = orchestrator.start_services(ROOT_DIR)
        return {"status": "started", "count": len(owned)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def detect_speaker_gender(media_path: Path) -> tuple[str, float]:
    """
    Analyzes input audio using multi-feature acoustic analysis:
    1. Speech-normalized and noise-reduced audio extraction (suppressing background music/piano).
    2. Linear Predictive Coding (LPC) formant analysis (F1, F2) reflecting physiological vocal tract length.
    3. YIN Pitch Tracking with subharmonic octave disambiguation (resolving deep male 2nd harmonic errors).
    
    Returns (gender, median_pitch_hz), where gender is 'male' or 'female'.
    """
    try:
        import numpy as np
        from scipy.linalg import toeplitz, solve

        # Extract speech with spectral noise reduction and normalization to suppress background music
        cmd = [
            "ffmpeg", "-y",
            "-i", str(media_path),
            "-af", "afftdn=nf=-25,highpass=f=70,lowpass=f=3500,speechnorm=e=4:r=0.0001:l=1",
            "-f", "s16le",
            "-ac", "1",
            "-ar", "16000",
            "-vn",
            "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or len(res.stdout) < 3200:
            return "male", 125.0

        samples = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float64)
        sr = 16000

        # ── 1. LPC Formant Tracking (F1, F2: Vocal Tract Anatomy) ─────────────
        emphasized = np.append(samples[0], samples[1:] - 0.97 * samples[:-1])
        frame_len_lpc = int(sr * 0.030)
        hop_lpc = int(sr * 0.015)
        f1_list, f2_list = [], []

        for i in range(0, len(emphasized) - frame_len_lpc, hop_lpc):
            w = emphasized[i : i + frame_len_lpc]
            if np.mean(w ** 2) < 1e5:
                continue
            w = w * np.hamming(len(w))
            order = 16
            r = np.correlate(w, w, mode="full")[len(w) - 1 : len(w) + order]
            if r[0] <= 0:
                continue
            try:
                R = toeplitz(r[:-1])
                a = solve(R, -r[1:])
                lpc = np.concatenate(([1], a))
                roots = np.roots(lpc)
                roots = [rt for rt in roots if np.imag(rt) > 0.01 and np.abs(rt) > 0.70]
                angz = np.arctan2(np.imag(roots), np.real(roots))
                formants = sorted(angz * (sr / (2 * np.pi)))
                formants = [f for f in formants if 250 <= f <= 3500]
                if len(formants) >= 2:
                    f1_list.append(formants[0])
                    f2_list.append(formants[1])
            except Exception:
                continue

        med_f1 = float(np.median(f1_list)) if f1_list else 500.0
        med_f2 = float(np.median(f2_list)) if f2_list else 1500.0

        # ── 2. YIN Pitch Tracking with Harmonic Octave Disambiguation ───────────
        frame_len = int(sr * 0.040)
        hop_len = int(sr * 0.015)
        num_frames = (len(samples) - frame_len) // hop_len
        if num_frames <= 0:
            return "male", 125.0

        min_lag = int(sr / 320)  # lag 50 (320 Hz)
        max_lag = int(sr / 75)   # lag 213 (75 Hz)

        energies = np.array([np.mean(samples[i * hop_len : i * hop_len + frame_len] ** 2) for i in range(num_frames)])
        e_thresh = np.percentile(energies, 30)
        if e_thresh < 1e5:
            e_thresh = 1e5

        f0_list = []

        for i in range(num_frames):
            if energies[i] < e_thresh:
                continue

            frame = samples[i * hop_len : i * hop_len + frame_len]
            zcr = np.mean(np.abs(np.diff(np.sign(frame)))) / 2.0
            if zcr > 0.32:
                continue

            w_len = len(frame)
            d = np.zeros(max_lag + 1)
            for tau in range(min_lag, max_lag + 1):
                diff = frame[:w_len - tau] - frame[tau:w_len]
                d[tau] = np.sum(diff ** 2) / (w_len - tau)

            cmndf = np.zeros(max_lag + 1)
            cmndf[min_lag] = 1.0
            running_sum = 0.0
            for tau in range(1, max_lag + 1):
                running_sum += d[tau]
                if running_sum > 0:
                    cmndf[tau] = (d[tau] * tau) / running_sum
                else:
                    cmndf[tau] = 1.0

            minima = []
            for tau in range(min_lag + 1, max_lag):
                if cmndf[tau] < cmndf[tau - 1] and cmndf[tau] < cmndf[tau + 1]:
                    if cmndf[tau] < 0.30:
                        minima.append((tau, cmndf[tau]))

            if not minima:
                continue

            chosen_tau = minima[0][0]
            best_tau, best_val = min(minima, key=lambda x: x[1])

            # Check if an octave subharmonic tau2 ≈ 2 * tau1 exists:
            # Resolves deep male chest resonance / 2nd harmonic dominance
            has_subharmonic = False
            for tau1, val1 in minima:
                for tau2, val2 in minima:
                    if tau2 > tau1 and 1.80 <= (tau2 / tau1) <= 2.20:
                        if (val2 < 0.25 or val2 < val1 + 0.12) and (med_f1 < 540 or med_f2 < 1650):
                            chosen_tau = tau2
                            has_subharmonic = True
                            break
                if has_subharmonic:
                    break

            if not has_subharmonic:
                chosen_tau = best_tau

            f0_list.append(sr / chosen_tau)

        if not f0_list:
            return "male", 125.0

        p_low, p_high = np.percentile(f0_list, 10), np.percentile(f0_list, 90)
        trimmed = [f for f in f0_list if p_low <= f <= p_high] or f0_list
        med_f0 = float(np.median(trimmed)) if trimmed else 125.0

        # ── 3. Multi-Feature Acoustic Decision ────────────────────────────────
        if med_f0 < 145:
            gender = "male"
        elif med_f0 >= 170:
            if med_f1 > 540 and med_f2 > 1650:
                gender = "female"
            elif med_f1 < 510 and med_f2 < 1550:
                # Strong male vocal tract formants override harmonic octave error
                gender = "male"
                med_f0 = round(med_f0 / 2.0, 1)
            else:
                gender = "female" if (med_f1 + med_f2 / 3.0) > 1050 else "male"
        else:
            # Boundary zone (145-170 Hz): disambiguate using formant acoustic space
            gender = "male" if (med_f1 < 520 or med_f2 < 1600) else "female"

        return gender, round(med_f0, 1)
    except Exception:
        return "male", 125.0


def _run_job_worker(
    job_id: str,
    input_video_path: Path,
    work_dir: Path,
    voice_gender: str = "auto",
    custom_voice: Optional[str] = None,
    target_language: str = "hindi",
):
    job = job_store[job_id]
    try:
        # Probe video duration using ffprobe
        video_duration = 0.0
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(input_video_path)]
            probe_res = subprocess.run(cmd, capture_output=True, text=True)
            if probe_res.returncode == 0:
                video_duration = float(json.loads(probe_res.stdout)["format"]["duration"])
        except Exception:
            pass
        job["video_duration"] = video_duration
        if video_duration > 0:
            job["logs"].append(f"Source video detected: {video_duration:.2f} seconds duration")

        job["status"] = "running"
        job["current_step"] = 1
        job["step_name"] = "Extracting Audio (Stage 01)"
        job["progress"] = 10
        job["logs"].append("Stage 01: Demuxing video audio track with FFmpeg...")

        # Stage 01
        with input_video_path.open("rb") as f:
            r = orchestrator.call("mp4_to_mp3", "/extract", files={"file": (input_video_path.name, f)})
        mp3_path = work_dir / "audio.mp3"
        mp3_path.write_bytes(r.content)
        job["logs"].append(f"Stage 01: Audio saved to audio.mp3 ({len(r.content)} bytes)")

        # Acoustic Speaker Gender & Pitch Detection (YIN algorithm)
        spk_gender, spk_pitch = detect_speaker_gender(mp3_path)
        job["detected_speaker_gender"] = spk_gender
        job["speaker_pitch_hz"] = spk_pitch

        req_gender = (voice_gender or "auto").strip().lower()
        if req_gender in ("male", "female"):
            effective_gender = req_gender
            job["logs"].append(
                f"Stage 01: Speaker voice acoustic profile -> {spk_gender.upper()} voice detected ({spk_pitch:.1f} Hz). "
                f"User voice override active -> using {effective_gender.upper()} voice."
            )
        else:
            effective_gender = spk_gender
            job["logs"].append(
                f"Stage 01: Speaker voice acoustic profile -> {spk_gender.upper()} voice automatically recognized & matched ({spk_pitch:.1f} Hz fundamental pitch)"
            )
        job["speaker_gender"] = effective_gender

        # Stage 02
        job["current_step"] = 2
        job["step_name"] = "Transcribing Speech (Stage 02 Whisper)"
        job["progress"] = 25
        job["logs"].append("Stage 02: Transcribing speech with faster-whisper neural model...")
        with mp3_path.open("rb") as f:
            r = orchestrator.call("mp3_to_text", "/api/transcribe", files={"file": ("audio.mp3", f)}, data={"language": "auto"})
        res2 = orchestrator.json_result(r, "mp3_to_text")
        text = str(res2.get("text", "")).strip()
        lang_label = str(res2.get("language_label", "Auto"))
        (work_dir / "transcript.txt").write_text(text, encoding="utf-8")
        job["transcript"] = text
        job["detected_language"] = lang_label
        job["logs"].append(f"Stage 02: Transcription completed ({lang_label}, {len(text.split())} words)")

        # Stage 03
        job["current_step"] = 3
        job["step_name"] = "Extracting Salient Keywords (Stage 03 Auto-Intelligence)"
        job["progress"] = 40
        job["logs"].append("Stage 03: Extracting salient domain keywords via adaptive knee detection...")
        r = orchestrator.call("text_to_kw", "/api/extract-keywords", json={"text": text, "top_n": None, "mode": "auto"})
        res3 = orchestrator.json_result(r, "text_to_kw")
        keywords = res3.get("keywords_in_order", [])
        (work_dir / "keywords.json").write_text(json.dumps(keywords, ensure_ascii=False, indent=2), encoding="utf-8")
        job["keywords"] = keywords
        job["logs"].append(f"Stage 03: Auto-extracted {len(keywords)} salient ordered keywords: {keywords}")


        # Stage 04
        job["current_step"] = 4
        job["step_name"] = "Reconstructing Sentences (Stage 04 Seq2Seq)"
        job["progress"] = 55
        job["logs"].append("Stage 04: Reconstructing syntax with T5 neural model...")
        keyword_text = ", ".join(keywords) if keywords else text
        
        # Try calling Stage 04 via HTTP if running, fallback to in-process construct
        constructed_sentence = ""
        try:
            r4 = requests.post("http://127.0.0.1:8004/api/construct", json={"text": keyword_text, "num_beams": 4}, timeout=30)
            if r4.ok:
                constructed_sentence = r4.json().get("output_sentence", "").strip()
        except Exception:
            pass

        if not constructed_sentence:
            stage4_dir = ROOT_DIR / "04_Keyword_to_Sentence_Construction"
            if str(stage4_dir) not in sys.path:
                sys.path.insert(0, str(stage4_dir))
            import importlib
            construct_mod = importlib.import_module("construct")
            SentenceConstructor = getattr(construct_mod, "SentenceConstructor")
            constructor = SentenceConstructor(model_path=str(stage4_dir / "saved_model"))
            constructed_sentence = constructor.construct(keyword_text).strip()

        (work_dir / "constructed_sentence.txt").write_text(constructed_sentence, encoding="utf-8")
        job["constructed_sentence"] = constructed_sentence
        job["logs"].append(f"Stage 04: Reconstructed sentence: '{constructed_sentence[:60]}...'")

        # Stage 05b: Sentence Reformation & Translation (Directly from Stage 04, skipping 05a)
        job["current_step"] = 5
        job["step_name"] = "Sentence Reformation & Translation (Stage 05b)"
        job["progress"] = 70
        job["logs"].append("Stage 05b: Removing disfluencies and preparing dubbed vernacular speech...")
        
        # When dubbing video, preserve full spoken dialogue context from transcript while removing disfluencies
        reformation_input = text if len(text.split()) >= len(constructed_sentence.split()) else constructed_sentence
        r = orchestrator.call("sentence_reformation", "/api/pipeline", json={"text": reformation_input, "target_language": "hindi"})
        res5b = orchestrator.json_result(r, "sentence_reformation")
        
        # Default to full meaningful translation so speech covers the full video! (step1_meaningful_hindi)
        # Use précis (step2_precise_hindi) only if explicitly configured
        dub_mode = job.get("dub_mode", "full")
        if dub_mode == "precis":
            final_text = str(res5b.get("step2_precise_hindi") or res5b.get("step1_meaningful_hindi") or "").strip()
        else:
            final_text = str(res5b.get("step1_meaningful_hindi") or res5b.get("step2_precise_hindi") or "").strip()

        (work_dir / "reformed_text.json").write_text(json.dumps(res5b, ensure_ascii=False, indent=2), encoding="utf-8")
        (work_dir / "dubbed_text.txt").write_text(final_text, encoding="utf-8")
        job["dubbed_text"] = final_text
        job["logs"].append(f"Stage 05b: Prepared {len(final_text.split())} words for speech synthesis: '{final_text[:60]}...'")

        # Stage 06
        job["current_step"] = 6
        job["step_name"] = "Neural Speech Synthesis (Stage 06 TTS)"
        job["progress"] = 85

        # Calculate dynamic pacing rate to match ~85%-92% of original video duration
        tts_rate = "+0%"
        word_count = len(final_text.split())
        if video_duration > 8 and word_count > 0:
            est_dur = word_count / 2.25  # ~2.25 words per second in Hindi TTS
            target_speech_dur = min(video_duration * 0.88, video_duration - 1.2)
            speed_factor = est_dur / target_speech_dur
            rate_val = int((speed_factor - 1.0) * 100)
            rate_val = max(-20, min(25, rate_val))
            tts_rate = f"{rate_val:+d}%"

        # Select neural voice matching detected/selected input speaker gender
        speaker_gender = job.get("speaker_gender", "male")
        target_lang = target_language.strip().lower()

        if custom_voice and custom_voice.strip():
            chosen_voice = custom_voice.strip()
        elif "bengali" in target_lang or target_lang == "bn":
            chosen_voice = "bn-IN-BashkarNeural" if speaker_gender == "male" else "bn-IN-TanishaaNeural"
        else:
            chosen_voice = "hi-IN-MadhurNeural" if speaker_gender == "male" else "hi-IN-SwaraNeural"

        job["chosen_voice"] = chosen_voice
        job["logs"].append(f"Stage 06: Generating natural neural {speaker_gender.upper()} speech via Edge TTS ({chosen_voice}, pacing rate: {tts_rate})...")
        r = orchestrator.call("text_to_mp3", "/api/synthesize", json={"text": final_text, "voice": chosen_voice, "rate": tts_rate})
        res6 = orchestrator.json_result(r, "text_to_mp3")
        audio_url = str(res6.get("audio_url", ""))
        audio_subpath = audio_url[audio_url.find("/api/audio/"):] if "/api/audio/" in audio_url else audio_url
        dubbed_mp3_path = work_dir / "dubbed_audio.mp3"
        dubbed_mp3_path.write_bytes(orchestrator.download("text_to_mp3", audio_subpath).content)
        job["logs"].append("Stage 06: Synthesized neural audio track saved")

        # Stage 07
        job["current_step"] = 7
        job["step_name"] = "Final Video & Audio Remuxing (Stage 07)"
        job["progress"] = 95
        job["logs"].append("Stage 07: Remuxing source video with dubbed audio track...")
        with input_video_path.open("rb") as vf, dubbed_mp3_path.open("rb") as af:
            r = orchestrator.call(
                "merge_mp3_mp4",
                "/api/merge",
                files={
                    "video": (input_video_path.name, vf, "video/mp4"),
                    "audio": ("dubbed_audio.mp3", af, "audio/mpeg"),
                },
            )
        res7 = orchestrator.json_result(r, "merge_mp3_mp4")
        video_url = str(res7.get("video_url", ""))
        video_subpath = video_url[video_url.find("/api/video/"):] if "/api/video/" in video_url else video_url
        final_video_path = work_dir / "final_dubbed_video.mp4"
        final_video_path.write_bytes(orchestrator.download("merge_mp3_mp4", video_subpath).content)

        job["current_step"] = 7
        job["step_name"] = "Pipeline Complete"
        job["progress"] = 100
        job["status"] = "completed"
        job["final_video_available"] = True
        job["logs"].append("[DONE] Pipeline execution completed successfully!")

    except (Exception, SystemExit) as exc:
        job["status"] = "error"
        job["error"] = str(exc)
        job["logs"].append(f"[ERROR] Pipeline halted: {exc}")


@app.post("/api/run-pipeline")
async def start_pipeline_job(
    file: UploadFile = File(...),
    voice_gender: str = Form("auto"),
    voice: Optional[str] = Form(None),
    target_language: str = Form("hindi"),
):
    """Uploads video and initiates asynchronous end-to-end dubbing pipeline with voice gender control."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}:
        raise HTTPException(status_code=400, detail="Invalid video format. Supported: .mp4, .mov, .mkv, .avi, .webm")

    job_id = f"job_{uuid.uuid4().hex[:8]}"
    work_dir = JOBS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    input_path = work_dir / f"input_video{suffix}"
    with open(input_path, "wb") as out_f:
        while chunk := await file.read(1024 * 1024):
            out_f.write(chunk)

    job_store[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "status": "pending",
        "progress": 0,
        "current_step": 0,
        "step_name": "Initializing",
        "logs": ["Job created. Video uploaded to disk."],
        "created_at": time.time(),
        "final_video_available": False,
        "requested_voice_gender": voice_gender,
        "requested_voice": voice,
        "target_language": target_language,
    }

    t = threading.Thread(
        target=_run_job_worker,
        args=(job_id, input_path, work_dir, voice_gender, voice, target_language),
        daemon=True,
    )
    t.start()

    return {"job_id": job_id, "status": "started"}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store[job_id]


@app.get("/api/jobs/{job_id}/final-video")
def get_final_video(job_id: str):
    video_path = JOBS_DIR / job_id / "final_dubbed_video.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Final dubbed video not ready yet")
    return FileResponse(str(video_path), media_type="video/mp4", filename=f"{job_id}_dubbed.mp4")


@app.get("/api/jobs/{job_id}/dubbed-audio")
def get_dubbed_audio(job_id: str):
    audio_path = JOBS_DIR / job_id / "dubbed_audio.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Dubbed audio not ready yet")
    return FileResponse(str(audio_path), media_type="audio/mpeg", filename=f"{job_id}_audio.mp3")


@app.get("/api/jobs/{job_id}/artifact/{name}")
def get_job_artifact(job_id: str, name: str):
    file_path = JOBS_DIR / job_id / name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(str(file_path), filename=name)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nativox Stage 00 Orchestrator Web Server")
    parser.add_argument("--auto-start", action="store_true", help="Automatically trigger background startup of all stage microservices")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default 8000)")
    args = parser.parse_args()

    if args.auto_start or os.environ.get("NATIVOX_AUTO_START_SERVICES") == "1":
        print("[*] Automatically triggering startup of missing microservices in background...")
        threading.Thread(target=orchestrator.start_services, args=(ROOT_DIR,), daemon=True).start()

    uvicorn.run("main:app", host="127.0.0.1", port=args.port, reload=False)

