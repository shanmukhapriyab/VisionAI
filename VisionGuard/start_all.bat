@echo off
setlocal
title VisionGuard Launcher
cd /d "%~dp0"

echo Starting the VisionGuard backend and frontend in two windows...
start "VisionGuard Backend" "%~dp0start_backend.bat"
start "VisionGuard Frontend" "%~dp0start_frontend.bat"

echo.
echo Waiting for the services. On the very first run this can take 10 to 20 minutes
echo while packages download. The browser opens automatically when both are ready.

set /a tries=0
:waitbackend
curl -s -f -o nul http://127.0.0.1:8000/api/health
if not errorlevel 1 goto waitfrontend
set /a tries+=1
if %tries% GEQ 600 goto timeout
timeout /t 3 /nobreak >nul
goto waitbackend

:waitfrontend
set /a tries=0
:loopfrontend
curl -s -f -o nul http://localhost:5173
if not errorlevel 1 goto ready
set /a tries+=1
if %tries% GEQ 100 goto timeout
timeout /t 2 /nobreak >nul
goto loopfrontend

:ready
echo Ready. Opening http://localhost:5173
start "" "http://localhost:5173"
echo You can close this launcher window. Close the two other windows to stop VisionGuard.
timeout /t 8 >nul
exit /b 0

:timeout
echo.
echo Timed out waiting for the services. Look at the Backend and Frontend windows for errors,
echo then open http://localhost:5173 manually once both say they are running.
pause
exit /b 1
