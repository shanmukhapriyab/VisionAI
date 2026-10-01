@echo off
setlocal
title VisionGuard Backend
cd /d "%~dp0backend"

rem ---- find Python -------------------------------------------------------
set "PYCMD="
where py >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3"
if not defined PYCMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD goto nopython

%PYCMD% -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto oldpython

rem ---- virtual environment -----------------------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  %PYCMD% -m venv .venv
  if errorlevel 1 goto venvfail
)
call ".venv\Scripts\activate.bat"

rem ---- dependencies, first run only --------------------------------------
if not exist ".venv\.deps_installed" (
  echo.
  echo Installing backend packages. This happens once and can take 5 to 15 minutes
  echo because it downloads PyTorch and YOLO. Please keep this window open.
  echo.
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  if errorlevel 1 goto pipfail
  echo done> ".venv\.deps_installed"
)

echo.
echo Starting VisionGuard backend at http://127.0.0.1:8000
echo The YOLO model loads in the background. Check http://127.0.0.1:8000/api/health
echo Close this window or press Ctrl+C to stop.
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo The backend has stopped.
pause
exit /b 0

:nopython
echo [ERROR] Python was not found.
echo Install Python 3.10, 3.11 or 3.12 from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" in the installer. Then run this file again.
pause
exit /b 1

:oldpython
echo [ERROR] Python 3.10 or newer is required. Please install a newer version from python.org.
pause
exit /b 1

:venvfail
echo [ERROR] Could not create the virtual environment.
pause
exit /b 1

:pipfail
echo.
echo [ERROR] Installing the packages failed. Check your internet connection and read the message above.
echo If the problem is PyTorch, use Python 3.11 or 3.12 (very new Python versions may lack wheels).
echo Delete the folder backend\.venv and run this file again to retry.
pause
exit /b 1
