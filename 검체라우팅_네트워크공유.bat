@echo off
chcp 65001 >nul
title 검체 자동 라우팅 시스템 - 네트워크 공유

cd /d "%~dp0"

:: Python / 가상환경 / 패키지 확인 (간략)
if not exist ".venv\Scripts\python.exe" (
    echo  가상환경이 없습니다. 먼저 [검체라우팅_실행.bat]을 한 번 실행하세요.
    pause
    exit /b 1
)

.venv\Scripts\python.exe -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo  패키지가 없습니다. 먼저 [검체라우팅_실행.bat]을 한 번 실행하세요.
    pause
    exit /b 1
)

:: 이 PC의 IP 주소 표시
echo.
echo  =========================================
echo   검체 라우팅 - 네트워크 공유 모드
echo  =========================================
echo.
echo  같은 네트워크의 다른 PC에서 아래 주소로 접속하세요:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /r "IPv4"') do (
    set IP=%%a
    setlocal EnableDelayedExpansion
    set IP=!IP: =!
    echo     http://!IP!:8000
    endlocal
)
echo.
echo  이 PC에서:  http://127.0.0.1:8000
echo.
echo  ─────────────────────────────────────────
echo   Windows 방화벽에서 8000 포트 허용 필요
echo   이 창을 닫으면 서버가 종료됩니다.
echo  ─────────────────────────────────────────
echo.

:: 포트 충돌 방지
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/dashboard"

.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000

echo.
echo  서버가 종료되었습니다.
pause
