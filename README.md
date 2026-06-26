# 검체관리프로그램

임상검사실 검체 소분류·미생물 배양 관리 시스템

FastAPI + SQLite + 번들 Python 3.11 — **파이썬 설치 없이 더블클릭으로 실행**

---

## 사용자 설치 (파이썬 불필요)

[**Releases 페이지**](../../releases/latest)에서 최신 버전을 다운로드하세요.

| 파일 | 대상 |
|------|------|
| `검체관리프로그램_설치_vX.X.X.zip` | 처음 설치하는 PC |
| `검체관리프로그램_업데이트_vX.X.X.zip` | 이미 설치된 PC — `app\` 폴더만 교체 |

**설치 방법**: ZIP 압축 해제 → `시작.bat` 더블클릭 → 브라우저 자동 오픈

> 자세한 안내는 ZIP 내 `문서\설치_안내서.pdf` 참고

---

## 주요 기능

- LIS Excel 파일 업로드 (접수 목록 일괄 등록)
- 검체 도착 관리 (바코드 스캐너 스캔)
- 미생물 소분류 자동 배정 (배양 타입 · 랙 · 칸 번호)
- TTS 음성 안내 (소분류 스캔 결과 낭독)
- 비미생물 학부별 소분류 현황
- 워크리스트 · 소분류 Excel 출력
- 출근 기준(19:00) 소분류 리셋
- 야간 근무(19:00 ~ 익일 09:00) 지원
- 네트워크 공유 (다른 PC 동시 접속)
- 대시보드 · 누락검체 · 미접수검체 조회

---

## 화면 목록

| 경로 | 설명 |
|------|------|
| `/dashboard` | 대시보드 |
| `/upload` | LIS 파일 업로드 |
| `/scan` | 검체 도착 스캔 |
| `/micro` | 미생물 소분류 스캔 |
| `/missing` | 누락검체 조회 |
| `/unregistered` | 미접수검체 조회 |
| `/find` | 검체 위치 검색 |

---

## 개발 환경 실행 (소스 코드에서)

```powershell
# 가상환경 생성
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 새 버전 배포

```bash
git add -A
git commit -m "feat: 변경 내용 요약"
git push origin main

# 새 버전 태그 → GitHub Actions가 자동으로 릴리즈 ZIP 생성
git tag v1.2.0
git push origin v1.2.0
```

태그를 푸시하면 `.github/workflows/release.yml` 워크플로우가 실행되어  
배포 ZIP 2종이 자동으로 [Releases](../../releases)에 업로드됩니다.

---

## 배포 파일 구조

```
검체관리프로그램/
├── app/               FastAPI 애플리케이션
├── python/            번들 Python 3.11 (모든 패키지 포함)
├── 문서/
│   ├── 설치_안내서.pdf
│   └── 관리자_안내서.pdf
├── 시작.bat
├── 네트워크공유.bat
└── 검체관리프로그램.exe
```

---

## 기술 스택

- **Backend**: FastAPI 0.115 · SQLAlchemy 2.0 · SQLite
- **Frontend**: Jinja2 · Bootstrap 5 · Web Speech API
- **Excel**: openpyxl 3.1
- **Runtime**: Python 3.11 embedded (번들 포함)
- **CI/CD**: GitHub Actions
