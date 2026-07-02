from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.branch_rack_service import (
    get_available_branch_codes,
    get_session,
    prepare_branch_rack,
    scan_branch_rack,
)

router = APIRouter(prefix="/api/branch-rack", tags=["branch-rack"])


class PrepareRequest(BaseModel):
    workstation_name: str
    branch_codes: list[str]
    rack_size: int = 50


class BranchRackScanRequest(BaseModel):
    accession_no: str
    workstation_name: str
    operator_name: str | None = None


@router.get("/codes")
def get_codes(db: Session = Depends(get_db)):
    """현재 DB에 있는 접수번호로부터 분류코드 목록 반환"""
    return {"codes": get_available_branch_codes(db)}


@router.post("/prepare")
def prepare(request: PrepareRequest, db: Session = Depends(get_db)):
    """선택된 분류코드로 세션 생성 및 랙 위치 사전 계산"""
    try:
        return prepare_branch_rack(
            db,
            request.workstation_name,
            request.branch_codes,
            request.rack_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/session")
def get_session_endpoint(workstation_name: str, db: Session = Depends(get_db)):
    """PC명으로 현재 세션 + 아이템 목록 조회 (폴링 엔드포인트)"""
    data = get_session(db, workstation_name)
    if not data:
        return {"session": None}
    return data


@router.post("/scan")
def scan(request: BranchRackScanRequest, db: Session = Depends(get_db)):
    """바코드 스캔 처리 — 랙 위치 반환 및 스캔 완료 표시"""
    return scan_branch_rack(
        db,
        request.accession_no,
        request.workstation_name,
        request.operator_name,
    )
