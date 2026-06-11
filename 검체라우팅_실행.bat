@echo off
chcp 65001 >nul
title 검체 자동 라우팅 시스템

echo.
echo  =========================================
echo   검체 자동 라우팅 시스템 - 시작 중...
echo  =========================================
echo.

:: 현재 배치 파일 위치로 이동
cd /d "%~dp0"

:: Python 존재 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo  [오류] Python이 설치되어 있지 않습니다.
    echo.
    echo  https://www.python.org/downloads/ 에서 Python 3.11 이상을 설치하세요.
    echo  설치 시 "Add Python to PATH" 옵션을 반드시 체크하세요.
    echo.
    pause
    exit /b 1
)

:: 가상환경 생성 (없으면)
if not exist ".venv\Scripts\python.exe" (
    echo  [1/3] 가상환경을 생성합니다...
    python -m venv .venv
    if errorlevel 1 (
        echo  [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )
    echo  완료.
    echo.
)

:: 패키지 설치 확인
.venv\Scripts\python.exe -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo  [2/3] 필요한 패키지를 설치합니다 (최초 1회)...
    .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo  [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하세요.
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

echo  [3/3] 서버를 시작합니다...
echo.
echo  접속 주소:  http://127.0.0.1:8000
echo.
echo  ─────────────────────────────────────────
echo   이 창을 닫으면 서버가 종료됩니다.
echo  ─────────────────────────────────────────
echo.

:: 3초 후 브라우저 자동 열기
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/dashboard"

:: 서버 실행
.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000

echo.
echo  서버가 종료되었습니다.
pause
