@echo off
cd /d %~dp0backend
if not exist venv (
    py -3.11 -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload
