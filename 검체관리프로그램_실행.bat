@echo off
chcp 65001 >nul
title 검체관리프로그램

cd /d "%~dp0"

echo.
echo  =========================================
echo   검체관리프로그램 - 시작 중...
echo  =========================================
echo.

:: 내장 Python 확인
if not exist "python\python.exe" (
    echo  [오류] python 폴더가 없습니다. 파일이 손상되었습니다.
    pause
    exit /b 1
)

set PYTHON=python\python.exe

:: 패키지 설치 확인 (최초 1회)
%PYTHON% -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo  [1/2] 필요한 패키지를 설치합니다 (최초 1회)...
    %PYTHON% -m pip install -r requirements.txt --no-warn-script-location --quiet
    if errorlevel 1 (
        echo  [오류] 패키지 설치 실패. 인터넷 연결을 확인하세요.
        pause
        exit /b 1
    )
    echo  완료.
    echo.
)

:: 포트 8000 사용 중이면 기존 프로세스 종료
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo  [2/2] 서버를 시작합니다...
echo.
echo  ─────────────────────────────────────────
echo   접속 주소:  http://127.0.0.1:8000
echo   이 창을 닫으면 서버가 종료됩니다.
echo  ─────────────────────────────────────────
echo.

:: 3초 후 브라우저 자동 열기
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/dashboard"

:: 서버 실행 (내장 Python uvicorn)
%PYTHON% -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo  서버가 종료되었습니다.
pause
