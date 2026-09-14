@echo off
cd /d "%~dp0backend"

if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt

echo.
echo Starting Text to Keyword at http://127.0.0.1:8010
echo Press Ctrl+C to stop.
echo.
python -m uvicorn main:app --reload --port 8010
