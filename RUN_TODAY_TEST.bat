@echo off
setlocal
cd /d "%~dp0"

set "APP_URL=http://127.0.0.1:8000/dashboard"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

echo ================================================
echo Specimen Routing MVP - Today Test Launcher
echo ================================================
echo.

if not exist "%PYTHON_EXE%" (
  echo Python environment was not found.
  echo Please run setup first, or use the original project folder.
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0.env" (
  echo .env file was not found.
  echo Database settings are required before running the app.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/dashboard' -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if "%ERRORLEVEL%"=="0" (
  echo App is already running. Opening browser...
  start "" "%APP_URL%"
  exit /b 0
)

echo Starting app server...
echo Keep the new black server window open during testing.
echo.

start "Specimen Routing MVP Server" cmd /k "cd /d "%~dp0" && "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Waiting for server startup...
timeout /t 4 /nobreak > nul

start "" "%APP_URL%"

echo.
echo Browser opened:
echo   %APP_URL%
echo.
echo If the page is not ready yet, wait 2-3 seconds and refresh.
timeout /t 3 /nobreak > nul
exit /b 0
