@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 검체관리프로그램

echo.
echo  ┌─────────────────────────────────────────┐
echo  │         검체관리프로그램  v1.0           │
echo  │   Laboratory Information System          │
echo  └─────────────────────────────────────────┘
echo.

:: ── 내장 Python 경로 확인 ──
set PYTHON="%~dp0python\python.exe"
if not exist %PYTHON% (
    echo [오류] python\python.exe 를 찾을 수 없습니다.
    echo        배포 패키지가 올바르게 압축 해제되었는지 확인하세요.
    pause
    exit /b 1
)

:: ── 포트 사용 여부 확인 ──
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [안내] 이미 8000번 포트에서 서버가 실행 중입니다.
    echo        Chrome에서 http://localhost:8000 을 열어 사용하세요.
    start "" "http://localhost:8000"
    pause
    exit /b 0
)

:: ── 서버 시작 ──
echo  서버를 시작합니다...
echo.
echo  ※ 이 창을 닫으면 프로그램이 종료됩니다.
echo  ※ 여러 PC에서 접속: http://[이 PC의 IP]:8000
echo.
echo  ┌─ 접속 주소 ──────────────────────────────┐
echo  │  같은 PC    :  http://localhost:8000      │

:: 네트워크 IP 표시
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    set IP=!IP: =!
)
setlocal enabledelayedexpansion
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set RAW=%%a
    set RAW=!RAW: =!
    echo  │  다른 PC    :  http://!RAW!:8000         │
    goto :show_done
)
:show_done
echo  └──────────────────────────────────────────┘
echo.

:: 3초 후 브라우저 자동 실행
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

:: uvicorn 실행 (단일 프로세스 비동기 — 동시접속 지원)
%PYTHON% -m uvicorn app.main:app ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --loop asyncio ^
    --no-access-log ^
    --timeout-keep-alive 30

echo.
echo  서버가 종료되었습니다.
pause
