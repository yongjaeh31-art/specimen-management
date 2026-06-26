@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 검체관리프로그램
cd /d "%~dp0"

if not exist "python\python.exe" (
    echo.
    echo  [오류] python 폴더를 찾을 수 없습니다.
    echo        배포 파일이 올바른지 확인하세요.
    echo.
    pause
    exit /b 1
)

:: 이미 실행 중이면 브라우저만 열기
netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo  서버가 이미 실행 중입니다. 브라우저를 엽니다...
    start "" "http://localhost:8000/dashboard"
    timeout /t 2 /nobreak >nul
    exit /b 0
)

:: 로컬 IP 자동 감지
set MYIP=
for /f "tokens=2 delims=:" %%A in ('ipconfig 2^>nul ^| findstr /i "IPv4"') do (
    set _TMP=%%A
    set _TMP=!_TMP: =!
    if not "!_TMP!"=="" (
        set MYIP=!_TMP!
        goto :ip_done
    )
)
:ip_done

echo.
echo  ==========================================
echo   검체관리프로그램  시작 중...
echo  ==========================================
echo.
echo   이 PC   :  http://localhost:8000
if not "!MYIP!"=="" (
    echo   다른 PC  :  http://!MYIP!:8000
)
echo.
echo   이 창을 닫으면 서버가 종료됩니다.
echo  ==========================================
echo.

start "" /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8000/dashboard"

python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log

echo.
echo  서버가 종료되었습니다.
pause
