import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AppUser


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        _, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    actual = _hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(actual, expected)


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "admin1234")


def check_admin_password(password: str) -> bool:
    return hmac.compare_digest(password or "", _admin_password())


def register_user(db: Session, username: str, display_name: str, password: str) -> dict:
    username = username.strip()
    display_name = display_name.strip()
    if len(username) < 2 or len(password) < 4 or not display_name:
        raise ValueError("아이디, 이름, 비밀번호를 확인해 주세요.")

    user = AppUser(
        username=username,
        display_name=display_name,
        password_hash=_hash_password(password),
        is_approved=False,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("이미 등록 요청된 아이디입니다.") from exc
    return _user_dict(user)


def login_user(db: Session, username: str, password: str) -> dict:
    user = db.query(AppUser).filter(AppUser.username == username.strip()).first()
    if not user or not _verify_password(password, user.password_hash):
        raise ValueError("아이디 또는 비밀번호가 맞지 않습니다.")
    if not user.is_active:
        raise ValueError("비활성화된 사용자입니다.")
    if not user.is_approved:
        raise ValueError("관리자 승인 대기 중입니다.")
    return _user_dict(user)


def approve_user(db: Session, user_id: int, admin_password: str) -> dict:
    if not check_admin_password(admin_password):
        raise ValueError("관리자 비밀번호가 맞지 않습니다.")
    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not user:
        raise ValueError("사용자를 찾을 수 없습니다.")
    user.is_approved = True
    user.approved_at = datetime.now(timezone.utc)
    db.commit()
    return _user_dict(user)


def pending_users(db: Session, admin_password: str) -> list[dict]:
    if not check_admin_password(admin_password):
        raise ValueError("관리자 비밀번호가 맞지 않습니다.")
    users = (
        db.query(AppUser)
        .filter(AppUser.is_approved.is_(False), AppUser.is_active.is_(True))
        .order_by(AppUser.created_at.asc())
        .all()
    )
    return [_user_dict(user) for user in users]


def _user_dict(user: AppUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_approved": user.is_approved,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
    }
