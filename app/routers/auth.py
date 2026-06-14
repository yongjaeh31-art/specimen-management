from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RegisteredPC
from app.schemas import AdminPasswordRequest, ApproveUserRequest, LoginRequest, PCRegisterRequest, RegisterRequest
from app.services.auth_service import approve_user, login_user, pending_users, register_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_user(db, request.username, request.display_name, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        return login_user(db, request.username, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pending")
def pending(request: AdminPasswordRequest, db: Session = Depends(get_db)):
    try:
        return pending_users(db, request.admin_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/approve")
def approve(request: ApproveUserRequest, db: Session = Depends(get_db)):
    try:
        return approve_user(db, request.user_id, request.admin_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pc-register")
def pc_register(request: PCRegisterRequest, db: Session = Depends(get_db)):
    """PC명 조회 → DB조회 → 없으면 자동등록"""
    pc_name = request.pc_name.strip()
    if not pc_name:
        raise HTTPException(status_code=400, detail="PC 이름을 입력해주세요.")
    existing = db.query(RegisteredPC).filter(RegisteredPC.pc_name == pc_name).first()
    if existing:
        return {
            "status": "exists",
            "pc_name": pc_name,
            "registered_at": existing.registered_at.isoformat() if existing.registered_at else None,
        }
    db.add(RegisteredPC(pc_name=pc_name, registered_by=request.registered_by))
    db.commit()
    return {"status": "registered", "pc_name": pc_name}
