@echo off
chcp 65001 >nul
title 배포 파일 빌드
cd /d "%~dp0"

echo.
echo  배포 파일을 생성합니다. 잠시 기다려주세요...
echo.

powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0빌드_배포파일.ps1"

echo.
pause
