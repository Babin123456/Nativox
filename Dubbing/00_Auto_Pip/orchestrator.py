import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

# Feature flag: Skip Stage 03 (Keywords) and Stage 04 (Sentence Construction) temporarily.
# When True, the speech transcript from Stage 02 is routed directly into Stage 05b (Reformation).
# Can be enabled/disabled here or via env var NATIVOX_SKIP_STAGES_3_4="0" (to enable) or "1" (to skip).
SKIP_STAGES_3_AND_4 = os.environ.get("NATIVOX_SKIP_STAGES_3_4", "1") == "1"

# One port per HTTP stage. Stage 04 is loaded directly from construct.py or via port 8004.
# Stage 2b (main.py) and Stage 6 (test_cloned.py) are executed in Stage 08 directly.
STAGES = {
    "mp4_to_mp3": "http://127.0.0.1:8001",
    "mp3_to_text": "http://127.0.0.1:8002",
    "text_to_kw": "http://127.0.0.1:8003",
    "kw_to_sentence": "http://127.0.0.1:8004",
    "kw_translation": "http://127.0.0.1:8011",
    "sentence_reformation": "http://127.0.0.1:8005",
    "text_to_mp3": "http://127.0.0.1:8006",
    "merge_mp3_mp4": "http://127.0.0.1:8007",
    "voice_extraction": "http://127.0.0.1:8008",
}

SERVICE_CONFIG = {
    "mp4_to_mp3": ("01_MP4_to_MP3", 8001, "/health"),
    "mp3_to_text": ("02_MP3_to_Text", 8002, "/api/languages"),
    "text_to_kw": ("03_Text_to_Keyword", 8003, "/api/health"),
    "sentence_reformation": ("05b_Sentence_Reformation__Atanu", 8005, "/api/health"),
    "text_to_mp3": ("06_Converted_Text_to_MP3", 8006, "/api/health"),
    "merge_mp3_mp4": ("07_Merge_MP3_with_MP4", 8007, "/api/health"),
}
STARTUP_TIMEOUT_SECONDS = 120


def wait_for_service(stage: str, health_path: str) -> None:
    """Wait until an HTTP stage accepts requests, or fail with its startup output."""
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    url = f"{STAGES[stage]}{health_path}"
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=3)
            if response.ok:
                return
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(1)
    raise SystemExit(
        f"Stage '{stage}' did not become ready at {url} within "
        f"{STARTUP_TIMEOUT_SECONDS} seconds ({last_error})."
    )


def start_services(root: Path, skip_stages_3_4: bool = SKIP_STAGES_3_AND_4) -> list[subprocess.Popen]:
    """Start missing HTTP stages and return only processes owned by this run."""
    owned_processes = []
    configs = dict(SERVICE_CONFIG)
    if skip_stages_3_4:
        configs.pop("text_to_kw", None)

    for stage, (relative_dir, port, health_path) in configs.items():
        try:
            response = requests.get(f"{STAGES[stage]}{health_path}", timeout=2)
            if response.ok:
                print(f"[ready] {stage} is already running on port {port}")
                continue
        except requests.RequestException:
            pass

        stage_dir = root / relative_dir
        if not stage_dir.is_dir():
            raise SystemExit(f"Directory for '{stage}' was not found: {stage_dir}")
        print(f"[start] {stage} on port {port}")
        stage_venv_py = stage_dir / "venv" / "Scripts" / "python.exe"
        python_bin = str(stage_venv_py) if stage_venv_py.is_file() else sys.executable
        env = os.environ.copy()
        env["TEMP"] = "D:\\tmp"
        env["TMP"] = "D:\\tmp"
        process = subprocess.Popen(
            [
                python_bin,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=stage_dir,
            env=env,
        )
        owned_processes.append(process)
        try:
            wait_for_service(stage, health_path)
        except SystemExit:
            stop_services(owned_processes)
            raise
    return owned_processes


def stop_services(processes: list[subprocess.Popen]) -> None:
    """Stop only service processes started by this pipeline invocation."""
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def call(stage: str, path: str, **kwargs) -> requests.Response:
    """Send one request to one stage, with clear error messages."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    url = f"{STAGES[stage]}{path}"
    try:
        response = requests.post(url, timeout=900, **kwargs)
    except requests.exceptions.ConnectionError as exc:
        raise SystemExit(
            f"Stage '{stage}' is not running at {url}. Start the services or run with auto-start enabled."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise SystemExit(f"Stage '{stage}' timed out while calling {url}.") from exc

    if not response.ok:
        detail = response.text.strip().replace("\n", " ")
        raise SystemExit(
            f"Stage '{stage}' failed ({response.status_code}): {detail[:300]}"
        )
    return response


def download(stage: str, path: str) -> requests.Response:
    """Download a generated file from one stage."""
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    url = f"{STAGES[stage]}{path}"
    try:
        response = requests.get(url, timeout=900)
    except requests.exceptions.ConnectionError as exc:
        raise SystemExit(
            f"Stage '{stage}' is not running at {url}. Start the services or run with auto-start enabled."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise SystemExit(f"Stage '{stage}' timed out while downloading {url}.") from exc

    if not response.ok:
        detail = response.text.strip().replace("\n", " ")
        raise SystemExit(
            f"Stage '{stage}' failed ({response.status_code}): {detail[:300]}"
        )
    return response


def json_result(response: requests.Response, stage: str) -> dict:
    """Parse a JSON response and report malformed stage output clearly."""
    try:
        result = response.json()
    except ValueError as exc:
        raise SystemExit(
            f"Stage '{stage}' returned invalid JSON: {response.text[:300]}"
        ) from exc
    if not isinstance(result, dict):
        raise SystemExit(f"Stage '{stage}' returned an invalid object response.")
    return result


def run_pipeline(
    mp4_path: str,
    work_dir: str | None = None,
    auto_start: bool = True,
    skip_stages_3_4: bool = SKIP_STAGES_3_AND_4,
) -> Path:
    input_path = Path(mp4_path).expanduser().resolve()
    if not input_path.is_file():
        raise SystemExit(f"Input video was not found: {input_path}")

    if work_dir is None:
        work_dir = str(Path(__file__).resolve().parent / "jobs" / "job1")
    work = Path(work_dir)
    work.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parent.parent
    owned_processes = start_services(root, skip_stages_3_4=skip_stages_3_4) if auto_start else []
    try:
        return _run_pipeline_steps(input_path, work, root, skip_stages_3_4=skip_stages_3_4)
    finally:
        stop_services(owned_processes)


def _run_pipeline_steps(
    input_path: Path,
    work: Path,
    root: Path,
    skip_stages_3_4: bool = SKIP_STAGES_3_AND_4,
) -> Path:
    # Stage 01: video -> audio
    print("[01] Extracting audio...")
    with input_path.open("rb") as f:
        r = call("mp4_to_mp3", "/extract", files={"file": (input_path.name, f)})
    mp3_path = work / "audio.mp3"
    mp3_path.write_bytes(r.content)
    print(f"     saved {mp3_path}")

    # Stage 02: Parallel execution of Stage 2a (Transcription) and Stage 2b (Voice Extraction via main.py)
    print("[02] Running Stage 2a (Transcription) and Stage 2b (Voice Extraction) in parallel...")
    stage08_dir = root / "08_Voice_extraction_translation"
    profile_json = work / "voice_profile.json"
    clips_dir = work / "voice_profile_clips"
    ref_wav = work / "voice_profile_reference.wav"

    def _run_stage_2a():
        print("  [02a] Transcribing speech with Whisper...")
        with mp3_path.open("rb") as f:
            r = call("mp3_to_text", "/api/transcribe",
                     files={"file": ("audio.mp3", f)},
                     data={"language": "auto"})
        res = json_result(r, "mp3_to_text")
        trans_text = str(res["text"]).strip()
        lang_lbl = str(res.get("language_label", "Auto"))
        (work / "transcript.txt").write_text(trans_text, encoding="utf-8")
        print(f"  [02a] Transcription completed ({lang_lbl}, {len(trans_text.split())} words)")
        return trans_text, lang_lbl

    def _run_stage_2b():
        print("  [02b] Extracting speaker voice acoustic profile & reference clips (main.py)...")
        stage08_py = root.parent / "LipSync_Babin" / ".venv" / "Scripts" / "python.exe"
        py_exec = str(stage08_py) if stage08_py.is_file() else sys.executable
        cmd_2b = [
            py_exec,
            str(stage08_dir / "main.py"),
            str(mp3_path),
            "--output-json", str(profile_json),
            "--clips-dir", str(clips_dir),
        ]
        res = subprocess.run(cmd_2b, cwd=str(stage08_dir), capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            err = res.stderr or res.stdout
            raise SystemExit(f"Stage 2b (Voice Extraction main.py) failed: {err[-500:]}")
        print(f"  [02b] Voice profile & clips generated successfully -> {profile_json}")
        return profile_json

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fut_2a = executor.submit(_run_stage_2a)
        fut_2b = executor.submit(_run_stage_2b)
        text, language_label = fut_2a.result()
        fut_2b.result()

    if skip_stages_3_4:
        # Stages 03 and 04 are temporarily skipped: route transcribed text directly to Stage 05b
        print("[03 & 04] Temporarily skipping Stage 03 (Keywords) and Stage 04 (Sentence Construction)...")
        print("          Routing Whisper transcript directly to Stage 05b (Sentence Reformation).")
        constructed_sentence = text
        (work / "constructed_sentence.txt").write_text(constructed_sentence, encoding="utf-8")
        (work / "keywords.json").write_text("[]", encoding="utf-8")
    else:
        # Stage 03: text -> keywords (Intelligent Auto-Extraction).
        print("[03] Extracting salient keywords (auto-adaptive)...")
        r = call("text_to_kw", "/api/extract-keywords", json={"text": text, "top_n": None, "mode": "auto"})
        result = json_result(r, "text_to_kw")

        try:
            keywords = result["keywords_in_order"]
            if not isinstance(keywords, list) or not all(isinstance(word, str) for word in keywords):
                raise TypeError("keywords_in_order must be a list of strings")
        except (KeyError, TypeError) as exc:
            raise SystemExit(
                f"Stage 'text_to_kw' returned an invalid response: {r.text[:300]}"
            ) from exc
        (work / "keywords.json").write_text(
            json.dumps(keywords, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"     {len(keywords)} keywords: {keywords}")

        # Stage 04: keywords -> grammatical sentence, loaded directly from construct.py.
        print("[04] Constructing a sentence from keywords...")
        keyword_text = ", ".join(keywords)
        stage4_dir = root / "04_Keyword_to_Sentence_Construction"
        if str(stage4_dir) not in sys.path:
            sys.path.insert(0, str(stage4_dir))
        try:
            import importlib
            construct_mod = importlib.import_module("construct")
            SentenceConstructor = getattr(construct_mod, "SentenceConstructor")
            model_dir = stage4_dir / "saved_model"
            constructor = SentenceConstructor(model_path=str(model_dir))
            constructed_sentence = constructor.construct(keyword_text).strip()
        except OSError as exc:
            if exc.errno == 4551 or "c10.dll" in str(exc):
                raise SystemExit(
                    "Stage 'kw_to_sentence' could not load PyTorch because Windows "
                    "Application Control blocked c10.dll. Ask your administrator to "
                    "approve the Python/PyTorch installation."
                ) from exc
            raise
        if not constructed_sentence:
            raise SystemExit("Stage 'kw_to_sentence' returned an empty sentence.")
        (work / "constructed_sentence.txt").write_text(
            constructed_sentence, encoding="utf-8"
        )
        print(f"     saved {work / 'constructed_sentence.txt'}")

    # Stage 05b: sentence -> meaningful Hindi translation & précis (skipping 05a).
    print("[05b] Re-forming and translating sentence (Stage 05b)...")
    r = call(
        "sentence_reformation",
        "/api/pipeline",
        json={"text": constructed_sentence, "target_language": "hindi"},
    )
    result = json_result(r, "sentence_reformation")
    try:
        meaningful_hindi = str(result["step1_meaningful_hindi"]).strip()
        precise_hindi = str(result["step2_precise_hindi"]).strip()
    except (KeyError, TypeError) as exc:
        raise SystemExit(
            f"Stage 'sentence_reformation' returned an invalid response: {r.text[:300]}"
        ) from exc
    final_text = precise_hindi or meaningful_hindi
    if not final_text:
        raise SystemExit("Stage 'sentence_reformation' returned empty Hindi text.")
    (work / "reformed_text.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (work / "dubbed_text.txt").write_text(final_text, encoding="utf-8")
    print(f"     saved {work / 'dubbed_text.txt'}")

    # Stage 06: Voice Synthesis
    dubbed_mp3_path = work / "dubbed_audio.mp3"
    cloned_wav_path = work / "dubbed_audio.wav"
    dubbed_text_file = work / "dubbed_text.txt"

    cloned_ok = False
    try:
        from TTS.api import TTS
        print("[06] Synthesizing cloned speech in author's voice (Stage 08 test_cloned.py)...")
        cmd_clone = [
            sys.executable,
            str(stage08_dir / "test_cloned.py"),
            "--text-file", str(dubbed_text_file),
            "--profile", str(profile_json),
            "--reference", str(ref_wav),
            "--clips-dir", str(clips_dir),
            "--output-mp3", str(dubbed_mp3_path),
            "--output-wav", str(cloned_wav_path),
        ]
        res_clone = subprocess.run(cmd_clone, cwd=str(stage08_dir), capture_output=True, text=True, encoding="utf-8")
        if res_clone.returncode == 0 and (dubbed_mp3_path.is_file() or cloned_wav_path.is_file()):
            cloned_ok = True
    except ImportError:
        pass

    if not cloned_ok:
        # Fallback to Stage 06 (06_Converted_Text_to_MP3) neural voice synthesis
        print("[06] Synthesizing Hindi speech via Stage 06 Neural TTS (hi-IN-MadhurNeural)...")
        r = call(
            "text_to_mp3",
            "/api/synthesize",
            json={"text": final_text, "voice": "hi-IN-MadhurNeural"},
        )
        result_tts = json_result(r, "text_to_mp3")
        audio_url = str(result_tts.get("audio_url", ""))
        audio_path = urlparse(audio_url).path
        dubbed_mp3_path.write_bytes(download("text_to_mp3", audio_path).content)

    if not dubbed_mp3_path.is_file() and cloned_wav_path.is_file():
        dubbed_mp3_path = cloned_wav_path
    print(f"     saved audio {dubbed_mp3_path}")

    # Stage 07: original MP4 + dubbed MP3 -> final MP4.
    print("[07] Merging dubbed audio with the original video...")
    audio_mime = "audio/mpeg" if dubbed_mp3_path.suffix == ".mp3" else "audio/wav"
    with input_path.open("rb") as video_file, dubbed_mp3_path.open("rb") as audio_file:
        r = call(
            "merge_mp3_mp4",
            "/api/merge",
            files={
                "video": (input_path.name, video_file, "video/mp4"),
                "audio": (dubbed_mp3_path.name, audio_file, audio_mime),
            },
        )
    result = json_result(r, "merge_mp3_mp4")
    try:
        video_url = str(result["video_url"])
        video_path = urlparse(video_url).path
    except (KeyError, TypeError) as exc:
        raise SystemExit(
            f"Stage 'merge_mp3_mp4' returned an invalid response: {r.text[:300]}"
        ) from exc
    if not video_path.startswith("/api/video/"):
        raise SystemExit(f"Stage 'merge_mp3_mp4' returned an unsafe video URL: {video_url}")
    final_video_path = work / "final_dubbed_video.mp4"
    final_video_path.write_bytes(download("merge_mp3_mp4", video_path).content)
    print(f"     saved {final_video_path}")

    return work


def check_services_status() -> None:
    print("[*] Checking status of Nativox microservices:")
    all_ok = True
    for stage, (relative_dir, port, health_path) in SERVICE_CONFIG.items():
        url = f"{STAGES[stage]}{health_path}"
        try:
            r = requests.get(url, timeout=2)
            if r.ok:
                print(f"  [ONLINE]  {stage:<22} port {port} -> {url}")
            else:
                print(f"  [ERROR]   {stage:<22} port {port} -> HTTP {r.status_code}")
                all_ok = False
        except requests.RequestException:
            print(f"  [OFFLINE] {stage:<22} port {port} -> {url}")
            all_ok = False
    print("Stage 04 (Sentence Construction) is loaded in-process or available on port 8004.")
    if all_ok:
        print("\n[+] All HTTP stage microservices are healthy and reachable.")
    else:
        print("\n[!] Some services are offline. Run orchestrator with auto-start enabled to launch them automatically.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(
            "Nativox Pipeline Orchestrator\n"
            "Usage:\n"
            '  python orchestrator.py "path/to/video.mp4" [--work-dir "output/folder"]\n'
            '  python orchestrator.py "path/to/video.mp4" --no-auto-start\n'
            '  python orchestrator.py "path/to/video.mp4" [--skip-stages-3-4 | --enable-stages-3-4]\n'
            "  python orchestrator.py --status\n"
            "  python orchestrator.py --start-services\n"
        )
        sys.exit(0)

    if sys.argv[1] in ("--status", "-s"):
        check_services_status()
        sys.exit(0)

    if sys.argv[1] == "--start-services":
        root = Path(__file__).resolve().parent.parent
        start_services(root)
        print("[+] All HTTP stages are ready.")
        sys.exit(0)

    input_argument = sys.argv[1]
    work_dir = None
    auto_start = True
    skip_stages_3_4 = SKIP_STAGES_3_AND_4

    args = list(sys.argv[2:])
    if "--enable-stages-3-4" in args:
        skip_stages_3_4 = False
        args.remove("--enable-stages-3-4")
    elif "--skip-stages-3-4" in args:
        skip_stages_3_4 = True
        args.remove("--skip-stages-3-4")

    if "--no-auto-start" in args:
        auto_start = False
        args.remove("--no-auto-start")

    if len(args) == 2 and args[0] == "--work-dir":
        work_dir = args[1]
    elif len(args) != 0:
        raise SystemExit(
            'Usage: python orchestrator.py "path/to/video.mp4" '
            '[--work-dir "output/folder"] [--no-auto-start] [--skip-stages-3-4|--enable-stages-3-4] [--status]'
        )
    run_pipeline(input_argument, work_dir, auto_start=auto_start, skip_stages_3_4=skip_stages_3_4)