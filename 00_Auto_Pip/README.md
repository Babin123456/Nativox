# Nativox automatic pipeline

`00_Auto_Pip` runs the complete Nativox video-dubbing workflow from a single
command. It uses one shared Python virtual environment for all pipeline
stages.

```text
MP4
  -> MP3
  -> transcript
  -> keywords
  -> constructed sentence
  -> translated keywords
  -> Hindi reformed text
  -> Hindi MP3
  -> final MP4
```

## Requirements

- Windows
- Python 3.11 or newer available through the `py` launcher
- `ffmpeg` available on `PATH` (required by Stages 01 and 07)
- A source video file in MP4 format

Stage 04 loads a PyTorch model from
`04_Keyword_to_Sentence_Construction\saved_model`. The first transcription run
may also take longer while its speech-recognition model is initialized.

## Setup

Run these commands once from this directory. The setup script creates `venv`
and installs the requirements used by all stages:

### PowerShell

```powershell
Set-Location "D:\path\to\Nativox\00_Auto_Pip"
& .\setup.bat
```

### Command Prompt

```bat
cd /d "D:\path\to\Nativox\00_Auto_Pip"
setup.bat
```

The setup script expects the numbered stage folders to be siblings of
`00_Auto_Pip`. Do not move this folder without moving it with the rest of the
Nativox project.

## Run the pipeline

`run_pipeline.bat` starts any missing HTTP services, runs every stage, and
stops only the services it started:

```bat
run_pipeline.bat "C:\path\to\video.mp4"
```

For example, the repository includes `test.mp4`:

```bat
run_pipeline.bat ".\test.mp4"
```

By default, results are written to `jobs\job1`. Pass a second argument to
choose a different output directory:

```bat
run_pipeline.bat "C:\path\to\video.mp4" "C:\path\to\output"
```

The equivalent direct Python command supports disabling automatic service
startup:

```bat
venv\Scripts\python.exe orchestrator.py "C:\path\to\video.mp4" --no-auto-start
venv\Scripts\python.exe orchestrator.py "C:\path\to\video.mp4" --work-dir "C:\path\to\output"
```

Use `--no-auto-start` only when the required services are already running.

## Manual service control

For development, start all seven HTTP services in separate console windows:

```bat
start_all.bat
```

Stage 04 is not an HTTP service; it is loaded directly from
`04_Keyword_to_Sentence_Construction\construct.py`.

Stop the services started by `start_all.bat` with:

```bat
stop_all.bat
```

`stop_all.bat` stops processes listening on the Nativox service ports. When
using `run_pipeline.bat`, services started by that invocation are stopped
automatically after the pipeline finishes.

## HTTP service ports

| Stage | Purpose | Port |
| --- | --- | ---: |
| 01 | MP4 to MP3 | 8001 |
| 02 | MP3 to text | 8002 |
| 03 | Text to keywords | 8003 |
| 05a | Keyword translation | 8011 |
| 05b | Sentence reformation | 8012 |
| 06 | Text to MP3 | 8013 |
| 07 | Merge MP3 with MP4 | 8014 |

Services bind to `127.0.0.1` and are used by the orchestrator only.

## Output files

The selected output directory contains the following files when the run
completes:

- `audio.mp3` - audio extracted from the source video
- `transcript.txt` - transcribed source audio
- `keywords.json` - extracted keywords
- `constructed_sentence.txt` - sentence generated from the keywords
- `translated_keywords.json` - translated keyword data
- `reformed_text.json` - sentence-reformation response
- `dubbed_text.txt` - final Hindi text used for speech synthesis
- `dubbed_audio.mp3` - synthesized Hindi audio
- `final_dubbed_video.mp4` - source video with the dubbed audio

## Troubleshooting

- **Python was not found:** install Python 3.11 or newer and ensure the `py`
  launcher is available.
- **Shared virtual environment not found:** run `setup.bat` before running the
  pipeline.
- **A service does not become ready:** verify that its port is not occupied,
  then run `stop_all.bat` and retry.
- **`ffmpeg` errors:** install FFmpeg and add its `bin` directory to `PATH`.
- **PyTorch `c10.dll` is blocked:** ask an administrator to approve the
  Python/PyTorch installation in Windows Application Control.
