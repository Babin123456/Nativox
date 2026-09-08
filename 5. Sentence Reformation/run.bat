@echo off
echo ============================================================
echo   Nativox - Stage 5: Sentence Reformation ^& Precis
echo ============================================================

cd /d "%~dp0backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install -r requirements.txt

echo.
echo Starting Stage 5 service on http://127.0.0.1:8012 ...
echo (Press CTRL+C to stop)
echo.

python -m uvicorn main:app --reload --port 8012
pause

