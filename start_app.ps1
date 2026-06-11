$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Python virtual environment was not found."
    Write-Host "Run these commands first:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .venv\Scripts\pip install -r requirements.txt"
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Starting specimen routing app..."
Write-Host ""
Write-Host "Open this address in Chrome:"
Write-Host "  http://localhost:8000"
Write-Host ""
Write-Host "Keep this window open while using the app."
Write-Host "Press Ctrl+C to stop the server."
Write-Host ""

& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
