from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
from app.models import OrderTest
from app.routers import auth, imports, micro, reports, scans
from app.schemas import DEPARTMENT_SUBCATEGORIES, MICRO_CULTURE_TYPES, SPECIMEN_CATEGORIES
from app.services.routing_service import seed_rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    db = SessionLocal()
    try:
        seed_rules(db)
        _migrate_test_names(db)
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(title="검체 자동 라우팅 시스템 MVP", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(imports.router)
app.include_router(scans.router)
app.include_router(micro.router)
app.include_router(reports.router)
app.include_router(auth.router)


def _migrate_test_names(db) -> None:
    """기존 DB 데이터 보정: 잘못 저장된 검사명/학부 수정"""
    # "A/S형광"으로 저장된 검사명 → 원래 이름으로 복원
    db.query(OrderTest).filter(OrderTest.test_name == "A/S형광").update(
        {"test_name": "AFB stain (항산성형광법)", "department_major": "A/S형광"},
        synchronize_session=False,
    )
    # 폐렴원인균 선별검사 학부 → 분자진단으로 보정
    db.query(OrderTest).filter(OrderTest.test_name.like("%폐렴원인균%")).update(
        {"department_major": "분자진단"},
        synchronize_session=False,
    )
    # "주간외주"로 저장된 검사명 → 원래 이름으로 복원, 학부 → 외주
    db.query(OrderTest).filter(OrderTest.test_name == "주간외주").update(
        {"test_name": "Fungus culture & Sensitivity (MIC)", "department_major": "외주"},
        synchronize_session=False,
    )
    # Dysmorphic RBC 학부 → 요경검으로 보정
    db.query(OrderTest).filter(OrderTest.test_name.like("%Dysmorphic RBC%")).update(
        {"department_major": "요경검"},
        synchronize_session=False,
    )


def ensure_schema_columns():
    inspector = inspect(engine)
    existing = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }
    additions = {
        "orders": {
            "patient_age": "VARCHAR(40)",
            "hospital_name": "VARCHAR(120)",
        },
        "specimen_arrivals": {"workstation_name": "VARCHAR(120)"},
        "scan_logs": {
            "operator_name": "VARCHAR(80)",
            "workstation_name": "VARCHAR(120)",
        },
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            if table not in existing:
                continue
            for column_name, column_type in columns.items():
                if column_name not in existing[table]:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/dashboard")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request):
    return templates.TemplateResponse("admin_users.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request, "categories": SPECIMEN_CATEGORIES})


@app.get("/micro", response_class=HTMLResponse)
def micro_page(request: Request):
    return templates.TemplateResponse(
        "micro.html",
        {
            "request": request,
            "culture_types": MICRO_CULTURE_TYPES,
            "micro_culture_types": MICRO_CULTURE_TYPES,
            "department_subcategories": DEPARTMENT_SUBCATEGORIES,
        },
    )


@app.get("/urine", response_class=HTMLResponse)
def urine_page(request: Request):
    return templates.TemplateResponse("urine.html", {"request": request})


@app.get("/missing", response_class=HTMLResponse)
def missing_page(request: Request):
    return templates.TemplateResponse("missing.html", {"request": request})


@app.get("/find", response_class=HTMLResponse)
def find_page(request: Request):
    return templates.TemplateResponse("find.html", {"request": request})


@app.get("/unregistered", response_class=HTMLResponse)
def unregistered_page(request: Request):
    return templates.TemplateResponse("unregistered.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
