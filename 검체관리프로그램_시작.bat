@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Specimen Management

echo.
echo  =========================================
echo   Specimen Management System  v1.0
echo   Laboratory Information System
echo  =========================================
echo.

if not exist "%~dp0python\python.exe" (
    echo [ERROR] python\python.exe not found.
    echo         Check folder: python\ app\ *.bat
    echo.
    pause
    exit /b 1
)

netstat -ano 2>nul | findstr ":8000" | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo [INFO] Server already running.
    echo        Open Chrome: http://localhost:8000
    start "" "http://localhost:8000"
    echo.
    pause
    exit /b 0
)

set MYIP=unknown
for /f "tokens=2 delims=:" %%A in ('ipconfig 2^>nul ^| findstr /i "IPv4"') do (
    set TMP=%%A
    set TMP=!TMP: =!
    if not "!TMP!"=="" (
        set MYIP=!TMP!
        goto :ip_done
    )
)
:ip_done

echo  Starting server...
echo.
echo  -----------------------------------------
echo   This PC  : http://localhost:8000
echo   Other PC : http://%MYIP%:8000
echo  -----------------------------------------
echo.
echo  [Keep this window open while using the app]
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul 2>nul && start http://localhost:8000"

"%~dp0python\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop asyncio --no-access-log --timeout-keep-alive 30

echo.
echo  Server stopped.
pause
