@echo off
setlocal
cd /d "%~dp0backend"

echo ===============================================
echo   Nativox - Stage 2: Audio to Text (ASR)
echo ===============================================

if not exist venv (
    echo Creating virtual environment with Python 3.11...
    py -3.11 -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install -r requirements.txt

echo.
echo Starting server on http://127.0.0.1:8001 ...
echo (Press CTRL+C to stop)
echo.

python -m uvicorn main:app --reload --port 8001
