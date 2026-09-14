#!/bin/bash
set -e

echo "==============================================="
echo "  Nativox - Keyword Translation stage"
echo "==============================================="

cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment with Python 3.11..."
    python3.11 -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

echo "Installing dependencies..."
python -m pip install -r requirements.txt

echo ""
echo "Starting server on http://127.0.0.1:8011 ..."
echo "(Press CTRL+C to stop)"
echo ""

python -m uvicorn main:app --reload --port 8011
