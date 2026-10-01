@echo off
setlocal
title VisionGuard Frontend
cd /d "%~dp0frontend"

where node >nul 2>nul
if errorlevel 1 goto nonode

if not exist "node_modules" (
  echo Installing frontend packages. This happens once and takes about a minute...
  call npm install --no-audit --no-fund
  if errorlevel 1 goto npmfail
)

echo.
echo Starting VisionGuard web app at http://localhost:5173
echo Close this window or press Ctrl+C to stop.
echo.
call npm run dev
echo.
echo The frontend has stopped.
pause
exit /b 0

:nonode
echo [ERROR] Node.js was not found.
echo Install the LTS version from https://nodejs.org/ then run this file again.
pause
exit /b 1

:npmfail
echo [ERROR] npm install failed. Check your internet connection and read the message above.
pause
exit /b 1
