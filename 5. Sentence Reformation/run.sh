#!/bin/bash
set -e

echo "============================================================"
echo "  Nativox - Stage 5: Sentence Reformation & Précis"
echo "============================================================"

cd "$(dirname "$0")/backend"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv || python -m venv venv
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

echo "Installing dependencies..."
"$PY_EXEC" -m pip install -r requirements.txt

echo ""
echo "Starting Stage 5 service on http://127.0.0.1:8012 ..."
echo "(Press CTRL+C to stop)"
echo ""

"$PY_EXEC" -m uvicorn main:app --reload --port 8012

