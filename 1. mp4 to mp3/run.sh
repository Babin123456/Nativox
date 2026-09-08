#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/backend"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
fi
python -m pip install -q -r requirements.txt

echo ""
echo "Starting server at http://127.0.0.1:8000"
echo ""
python -m uvicorn main:app --reload --port 8000
