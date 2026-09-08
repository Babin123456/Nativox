#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/backend"

echo "==============================================="
echo "  Nativox - Stage 2: Audio to Text (ASR)"
echo "==============================================="

if [ ! -d "venv" ]; then
  echo "Creating virtual environment with Python 3.11..."
  python3.11 -m venv venv || python3 -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
  PY_EXEC="venv/bin/python"
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
  PY_EXEC="venv/Scripts/python"
else
  PY_EXEC="python"
fi

"$PY_EXEC" -m pip install -r requirements.txt

echo ""
echo "Starting server on http://127.0.0.1:8001 ..."
echo "(Press CTRL+C to stop)"
echo ""

"$PY_EXEC" -m uvicorn main:app --reload --port 8001
