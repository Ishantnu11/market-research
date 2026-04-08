@echo off
TITLE Market Research App - Local Runner
setlocal enabledelayedexpansion

:: Get the directory of the script
cd /d "%~dp0"

echo ==========================================
echo   Market Research System - Local Runner
echo ==========================================

:: 1. Check for Virtual Environment
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please run the following command to set it up:
    echo python -m venv venv
    echo venv\Scripts\activate
    echo pip install -r requirements.txt
    pause
    exit /b
)

:: 2. Check for node_modules
if not exist "node_modules" (
    echo [WARNING] node_modules not found. 
    echo Attempting to install frontend dependencies...
    npm install
)

:: 3. Start Backend
echo [*] Starting Backend (Uvicorn on port 8001)...
:: Port 8001 is used based on .env.development and restart_backend.ps1
start "Backend (8001)" cmd /k "TITLE Backend (8001) && echo Starting Backend... && call venv\Scripts\activate && uvicorn main:app --reload --port 8001"

:: 4. Start Frontend
echo [*] Starting Frontend (Vite on port 5173)...
start "Frontend (5173)" cmd /k "TITLE Frontend (5173) && echo Starting Frontend... && npm run dev"

echo.
echo ------------------------------------------
echo Status: Services are launching in new windows.
echo.
echo Backend URL:  http://localhost:8001
echo Frontend URL: http://localhost:5173
echo ------------------------------------------
echo.
echo To stop everything, close the new windows or 
echo press Ctrl+C in their respective terminals.
echo.
pause
