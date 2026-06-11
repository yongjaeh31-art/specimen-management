# 검체 자동 라우팅 시스템 MVP

Windows 환경에서 크롬 브라우저와 키보드 입력 방식 바코드 스캐너로 사용할 수 있는 FastAPI + PostgreSQL 기반 MVP입니다.

## 주요 기능

- 접수리스트 Excel/CSV 업로드
- 1차, 2차, 3차 및 최종 업로드 표시
- 접수번호 기준 upsert, 기존 도착상태 유지
- 조회만 모드와 카테고리별 도착처리
- 접수리스트에 없는 스캔은 선도착 저장
- 최종 업로드 후에도 접수에 없으면 미접수검체로 표시
- 전체 검사항목, 학부 대분류 카드, 분주/전달 필요 표시
- 미생물 culture_type별 Hole 번호 발급
- PostgreSQL row lock 기반 번호 발급으로 동시 스캔 중복 방지
- 누락검체, 미접수검체, 미생물 소분류 현황, 대시보드 제공

## 프로젝트 구조

```text
app/main.py
app/database.py
app/models.py
app/schemas.py
app/services/import_service.py
app/services/scan_service.py
app/services/routing_service.py
app/services/micro_service.py
app/routers/imports.py
app/routers/scans.py
app/routers/micro.py
app/routers/reports.py
app/templates/
app/static/
requirements.txt
README.md
```

## Windows 실행 방법

기본 상태에서는 SQLite 데모 DB를 사용합니다. 여러 PC 동시 사용이나 베타 운영은 PostgreSQL로 전환하세요.

### 1. PostgreSQL 준비

처음 화면만 확인하려면 별도 DB 설치 없이 실행할 수 있습니다. `.env` 파일이 없으면 로컬 `specimen_routing.db` SQLite 파일을 사용합니다.

운영용으로는 PostgreSQL을 설치한 뒤 데이터베이스를 생성합니다.

```powershell
psql -U postgres
```

```sql
CREATE DATABASE specimen_routing;
\q
```

기본 접속 정보는 아래와 같습니다.

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/specimen_routing
```

PostgreSQL을 사용할 때는 프로젝트 루트에 `.env.example`을 복사해 `.env` 파일을 만들고 수정합니다.

```text
DATABASE_URL=postgresql+psycopg2://postgres:내비밀번호@localhost:5432/specimen_routing
```

또는 PostgreSQL 설치 후 `switch_to_postgres.ps1`를 실행해 `.env`를 자동 생성할 수 있습니다.

SQLite 데모 DB의 기존 데이터를 PostgreSQL로 옮기려면, PostgreSQL로 서버를 한 번 실행해 테이블을 만든 뒤 아래 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py
```

### 2. Python 가상환경 생성

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell 실행 정책 오류가 나면 아래 명령을 한 번 실행한 뒤 다시 활성화합니다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. 서버 실행

가상환경과 패키지 설치가 끝난 뒤에는 `start_app.bat`를 더블클릭해도 됩니다.

직접 실행하려면 아래 명령을 사용합니다.

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

브라우저에서 접속합니다.

```text
http://localhost:8000
```

다른 스캔 PC에서 접속하려면 서버 PC의 IP를 사용합니다.

```text
http://서버PC_IP:8000
```

Windows 방화벽에서 Python 또는 8000번 포트를 허용해야 다른 PC가 접속할 수 있습니다.

## 화면

- `/login` 로그인 및 신규 사용자 승인 요청
- `/admin/users` 사용자 승인
- `/upload` 접수리스트 업로드
- `/scan` 검체 조회/도착처리
- `/micro` 미생물 소분류 스캔
- `/missing` 누락검체
- `/unregistered` 미접수검체
- `/dashboard` 대시보드

## 접수리스트 컬럼

CSV, XLSX, XLS 파일을 지원합니다. 아래 한글/영문 컬럼명을 인식합니다.

| 의미 | 인식 컬럼명 |
| --- | --- |
| 접수번호 | `accession_no`, `접수번호`, `바코드`, `검체번호`, `등록번호` |
| 환자명 | `patient_name`, `환자명`, `성명` |
| 환자번호 | `patient_id`, `환자번호`, `차트번호` |
| 검체명 | `specimen_name`, `검체명`, `검체` |
| 검사코드 | `test_code`, `검사코드`, `code` |
| 검사항목 | `test_name`, `검사항목`, `검사명`, `검사` |
| 학부 | `department_major`, `학부`, `부서`, `대분류` |
| 분주필요 | `aliquot_required`, `분주필요`, `분주` |
| 전달필요 | `transfer_required`, `전달필요`, `전달` |

한 접수번호에 여러 검사항목이 있으면 여러 행으로 넣으면 됩니다.

## API

- `POST /api/import/orders`
- `POST /api/scan`
- `POST /api/micro/culture-scan`
- `GET /api/missing`
- `GET /api/unregistered`
- `GET /api/micro/culture-assignments`
- `GET /api/dashboard/summary`

## Hole 번호 규칙

미생물 소분류별로 `culture_rules.next_sequence`를 PostgreSQL `SELECT FOR UPDATE`로 잠그고 증가시킵니다. SQLite 데모 모드는 화면 확인용이며, 4~5대 PC 동시 스캔 운영은 PostgreSQL 설정으로 실행하세요.

- 1번: `U-R01-H001`
- 100번: `U-R01-H100`
- 101번: `U-R02-H001`

중복 기준은 `accession_no + culture_type`입니다. 이미 발급된 검체를 다시 스캔하면 기존 Hole 번호를 반환합니다.

## 운영 메모

- 신규 사용자는 `/login`에서 등록 요청 후 `/admin/users`에서 관리자 승인을 받아야 로그인할 수 있습니다.
- 기본 관리자 비밀번호는 `admin1234`입니다. 운영 전 `.env`에 `ADMIN_PASSWORD=원하는비밀번호`를 추가해 변경하세요.
- 일반 검체 도착 중복 기준은 `accession_no + specimen_category`입니다.
- 조회만 모드 또는 카테고리 미선택 상태에서는 도착처리하지 않고 검사정보만 표시합니다.
- 접수리스트에 없는 검체를 카테고리 선택 후 스캔하면 선도착으로 저장됩니다.
- 이후 업로드에서 같은 접수번호가 들어오면 선도착 기록이 접수 건과 연결됩니다.
- 최종 업로드가 된 뒤에도 접수에 없는 선도착은 미접수검체로 표시됩니다.
