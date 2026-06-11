from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.import_service import import_orders

router = APIRouter(prefix="/api/import", tags=["imports"])


@router.post("/orders")
async def import_order_file(
    file: UploadFile = File(...),
    batch_type: str = Form("1차"),
    is_final: bool = Form(False),
    db: Session = Depends(get_db),
):
    try:
        content = await file.read()
        return import_orders(db, file.filename or "orders", content, batch_type, is_final)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
