@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.10 or newer, then try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the project environment...
  py -m venv .venv
  if errorlevel 1 goto failed
)

".venv\Scripts\python.exe" -c "import streamlit" >nul 2>nul
if errorlevel 1 (
  echo Installing project packages. This needs an internet connection and may take a few minutes...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)

echo Starting AquaShield. Keep this window open while presenting.
".venv\Scripts\python.exe" -m streamlit run src/dashboard/app.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo AquaShield could not start. Read the error above, then ask for help with that message.
pause
exit /b 1
