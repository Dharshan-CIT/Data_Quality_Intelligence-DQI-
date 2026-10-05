@echo off
rem Double-click this file to start the DQI backend and frontend, then open the splash page.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Run:  py -3.13 -m venv .venv  and  .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

start "DQI Backend (port 8000)" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000"
start "DQI Frontend (port 5173)" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo Waiting for the servers to start...
ping -n 12 127.0.0.1 >nul
start "" "http://localhost:5173/intro"
echo Opened http://localhost:5173/intro
