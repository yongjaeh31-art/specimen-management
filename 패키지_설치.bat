@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 패키지 설치

echo.
echo  검체관리프로그램 — 패키지 설치
echo  =====================================
echo.

set PYTHON="%~dp0python\python.exe"
if not exist %PYTHON% (
    echo [오류] python\python.exe 를 찾을 수 없습니다.
    pause
    exit /b 1
)

echo  필요한 패키지를 설치합니다. 잠시 기다려주세요...
echo.

%PYTHON% -m pip install --upgrade pip --quiet
%PYTHON% -m pip install -r requirements.txt --quiet

if %errorlevel%==0 (
    echo.
    echo  ✓ 설치 완료!
    echo    이제 [검체관리프로그램_시작.bat] 를 실행하세요.
) else (
    echo.
    echo  [오류] 패키지 설치에 실패했습니다.
    echo        인터넷 연결을 확인하고 다시 시도하세요.
)
echo.
pause
