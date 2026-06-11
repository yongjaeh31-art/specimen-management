from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ScanRequest
from app.services.scan_service import scan_specimen

router = APIRouter(prefix="/api", tags=["scans"])


@router.post("/scan")
def scan(request: ScanRequest, db: Session = Depends(get_db)):
    return scan_specimen(
        db,
        request.accession_no,
        request.specimen_category,
        request.client_name,
        request.operator_name,
        request.workstation_name,
    )
