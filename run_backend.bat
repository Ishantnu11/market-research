@echo off
TITLE Backend Runner (8001)
cd /d "%~dp0"
echo Starting FastAPI Backend...
call venv\Scripts\activate
uvicorn main:app --reload --port 8001
pause
