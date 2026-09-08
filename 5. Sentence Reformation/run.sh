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
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

echo "Installing dependencies..."
python -m pip install -r requirements.txt

echo ""
echo "Starting Stage 5 service on http://127.0.0.1:8012 ..."
echo "(Press CTRL+C to stop)"
echo ""

python -m uvicorn main:app --reload --port 8012

