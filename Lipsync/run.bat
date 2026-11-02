@echo off
setlocal
cd /d "%~dp0backend"
if not exist "venv\Scripts\python.exe" (
  echo Creating Lipsync virtual environment...
  python -m venv venv
  if errorlevel 1 exit /b 1
  "venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 exit /b 1
)
"venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8020
