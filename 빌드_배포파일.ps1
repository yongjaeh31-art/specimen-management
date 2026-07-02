# 빌드_배포파일.ps1
# 실행: 빌드_배포파일.bat  (또는 PowerShell에서 직접 실행)
# 결과: 배포\ 폴더에 ZIP 2종 생성

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$date   = Get-Date -Format "yyyyMMdd"
$dist   = Join-Path $root "배포"
$stage  = Join-Path $root "_빌드임시"

New-Item -ItemType Directory -Force -Path $dist | Out-Null

$fullZip   = Join-Path $dist "검체관리프로그램_설치_$date.zip"
$updateZip = Join-Path $dist "검체관리프로그램_업데이트_$date.zip"

Write-Host ""
Write-Host "=== 검체관리프로그램 배포파일 빌드 ===" -ForegroundColor Cyan
Write-Host ""

# ── 임시 디렉토리 초기화 ───────────────────────────────────────────────
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }

# ──────────────────────────────────────────────────────────────────────
#  전체 설치 ZIP  (python + app + 런처)
# ──────────────────────────────────────────────────────────────────────
Write-Host "[1/6] 스테이징 디렉토리 생성..."
$pkg = Join-Path $stage "검체관리프로그램"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null

Write-Host "[2/6] 앱 코드 복사..."
$appDst = Join-Path $pkg "app"
Copy-Item (Join-Path $root "app") $appDst -Recurse
# __pycache__ 제거
Get-ChildItem $appDst -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

Write-Host "[3/6] Python 런타임 복사 중 (100MB+, 잠시 기다려주세요)..."
$pyDst = Join-Path $pkg "python"
Copy-Item (Join-Path $root "python") $pyDst -Recurse
Get-ChildItem $pyDst -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

Write-Host "[4/6] 런처 파일 복사..."
@("시작.bat", "네트워크공유.bat", "검체관리프로그램.exe") | ForEach-Object {
    $src = Join-Path $root $_
    if (Test-Path $src) {
        Copy-Item $src $pkg
        Write-Host "      + $_"
    }
}

# 문서 PDF 생성 후 포함
Write-Host "[4b/6] 문서 PDF 생성..."
$docsDir = Join-Path $pkg "문서"
New-Item -ItemType Directory -Force -Path $docsDir | Out-Null
$pyExe = Join-Path $root "python\python.exe"
if (Test-Path $pyExe) {
    & $pyExe (Join-Path $root "make_docs.py") 2>$null
    $docSrc = Join-Path $dist "문서"
    if (Test-Path $docSrc) {
        Get-ChildItem $docSrc -File | Where-Object { $_.Extension -in ".pdf",".docx" } | ForEach-Object {
            Copy-Item $_.FullName $docsDir
            Write-Host "      + 문서\$($_.Name)"
        }
    }
}

Write-Host "[5/6] ZIP 압축 중..."
if (Test-Path $fullZip) { Remove-Item $fullZip }
Compress-Archive -Path $pkg -DestinationPath $fullZip -CompressionLevel Optimal
$sz = [math]::Round((Get-Item $fullZip).Length / 1MB, 1)
Write-Host "  -> 전체 설치: $fullZip  ($sz MB)" -ForegroundColor Green

# ──────────────────────────────────────────────────────────────────────
#  업데이트 ZIP  (app 폴더만)
# ──────────────────────────────────────────────────────────────────────
Write-Host "[6/6] 업데이트 패키지 생성..."
$upStage = Join-Path $stage "update"
New-Item -ItemType Directory -Force -Path $upStage | Out-Null
$appUpDst = Join-Path $upStage "app"
Copy-Item (Join-Path $root "app") $appUpDst -Recurse
Get-ChildItem $appUpDst -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force

if (Test-Path $updateZip) { Remove-Item $updateZip }
Compress-Archive -Path $appUpDst -DestinationPath $updateZip -CompressionLevel Optimal
$sz2 = [math]::Round((Get-Item $updateZip).Length / 1MB, 1)
Write-Host "  -> 업데이트:  $updateZip  ($sz2 MB)" -ForegroundColor Green

# ── 임시 파일 정리 ────────────────────────────────────────────────────
Remove-Item $stage -Recurse -Force

Write-Host ""
Write-Host "=== 빌드 완료! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "배포 폴더: $dist"
Write-Host ""
Write-Host "  [전체 설치]  검체관리프로그램_설치_$date.zip"
Write-Host "    - 파이썬 없는 PC에 처음 설치할 때 사용"
Write-Host "    - ZIP 압축 해제 후 '시작.bat' 또는 '검체관리프로그램.exe' 실행"
Write-Host ""
Write-Host "  [업데이트]   검체관리프로그램_업데이트_$date.zip"
Write-Host "    - 기존 설치 PC에 앱만 업데이트할 때 사용"
Write-Host "    - 기존 설치 폴더의 app\ 폴더를 덮어쓰기"
Write-Host ""
