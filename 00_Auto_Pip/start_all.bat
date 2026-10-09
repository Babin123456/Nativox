@echo off
setlocal

set "ROOT=%~dp0.."
set "PYTHON=%~dp0venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Shared virtual environment not found.
    echo Run setup.bat first.
    exit /b 1
)

start "01 MP4 to MP3" /D "%ROOT%\01_MP4_to_MP3\backend" "%PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 8001
start "02 MP3 to Text" /D "%ROOT%\02_MP3_to_Text\backend" "%PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 8002
start "03 Text to Keyword" /D "%ROOT%\03_Text_to_Keyword\backend" "%PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 8003

echo Started the first three stages.
echo Close the server windows or run stop_all.bat to stop them.