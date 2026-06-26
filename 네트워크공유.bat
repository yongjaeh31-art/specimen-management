@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 검체관리프로그램 - 네트워크 공유
cd /d "%~dp0"

if not exist "python\python.exe" (
    echo  [오류] python 폴더를 찾을 수 없습니다.
    pause & exit /b 1
)

:: 이미 실행 중이면 브라우저만 열기
netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo  서버가 이미 실행 중입니다. 브라우저를 엽니다...
    start "" "http://localhost:8000/dashboard"
    exit /b 0
)

:: Windows 방화벽에서 8000 포트 허용 (관리자 권한 필요, 실패해도 계속)
netsh advfirewall firewall show rule name="검체관리프로그램" >nul 2>&1
if %errorlevel% neq 0 (
    netsh advfirewall firewall add rule name="검체관리프로그램" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
)

:: 모든 IPv4 주소 표시
echo.
echo  ==========================================
echo   검체관리프로그램 - 네트워크 공유 모드
echo  ==========================================
echo.
echo   같은 네트워크의 다른 PC에서 아래 주소로 접속:
echo.
for /f "tokens=2 delims=:" %%A in ('ipconfig 2^>nul ^| findstr /i "IPv4"') do (
    set _IP=%%A
    set _IP=!_IP: =!
    if not "!_IP!"=="" echo     http://!_IP!:8000
)
echo.
echo   이 PC:  http://localhost:8000
echo.
echo   이 창을 닫으면 서버가 종료됩니다.
echo  ==========================================
echo.

start "" /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8000/dashboard"

python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log

echo.
echo  서버가 종료되었습니다.
pause
