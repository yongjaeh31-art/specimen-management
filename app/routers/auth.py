from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AdminPasswordRequest, ApproveUserRequest, LoginRequest, RegisterRequest
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
