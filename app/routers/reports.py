from sqlalchemy import distinct, func
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ImportBatch, MicroCultureAssignment, Order, SpecimenArrival
from app.services.barcode_service import normalize_accession_input
from app.services.routing_service import build_department_cards
from app.services.scan_service import find_order_by_accession

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/missing")
def missing(db: Session = Depends(get_db)):
    latest_final = db.query(ImportBatch).filter(ImportBatch.is_final.is_(True)).order_by(ImportBatch.id.desc()).first()
    query = (
        db.query(Order)
        .outerjoin(SpecimenArrival, Order.accession_no == SpecimenArrival.accession_no)
        .filter(SpecimenArrival.id.is_(None))
    )
    if latest_final:
        query = query.filter(Order.is_in_final_batch.is_(True))
    rows = query.order_by(Order.accession_no).all()
    return [
        {
            "accession_no": row.accession_no,
            "patient_name": row.patient_name,
            "specimen_name": row.specimen_name,
            "is_in_final_batch": row.is_in_final_batch,
        }
        for row in rows
    ]


@router.get("/unregistered")
def unregistered(db: Session = Depends(get_db)):
    latest_final = db.query(ImportBatch).filter(ImportBatch.is_final.is_(True)).order_by(ImportBatch.id.desc()).first()
    query = (
        db.query(SpecimenArrival)
        .outerjoin(Order, SpecimenArrival.accession_no == Order.accession_no)
        .filter(Order.id.is_(None))
        .order_by(SpecimenArrival.arrived_at.desc())
    )
    return [
        {
            "accession_no": row.accession_no,
            "specimen_category": row.specimen_category,
            "arrived_at": row.arrived_at.isoformat() if row.arrived_at else None,
            "arrived_by": row.arrived_by,
            "workstation_name": row.workstation_name,
            "status": "미접수검체" if latest_final else "선도착",
        }
        for row in query.all()
    ]


@router.get("/dashboard/summary")
def summary(db: Session = Depends(get_db)):
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    arrived_accessions = db.query(func.count(distinct(SpecimenArrival.accession_no))).scalar() or 0
    unregistered_count = (
        db.query(func.count(SpecimenArrival.id))
        .outerjoin(Order, SpecimenArrival.accession_no == Order.accession_no)
        .filter(Order.id.is_(None))
        .scalar()
        or 0
    )
    micro_count = db.query(func.count(MicroCultureAssignment.id)).scalar() or 0
    final_batch = db.query(ImportBatch).filter(ImportBatch.is_final.is_(True)).order_by(ImportBatch.id.desc()).first()
    return {
        "total_orders": total_orders,
        "arrived_accessions": arrived_accessions,
        "missing_count": max(total_orders - arrived_accessions, 0),
        "unregistered_count": unregistered_count,
        "micro_assignment_count": micro_count,
        "has_final_batch": final_batch is not None,
        "latest_final_batch_id": final_batch.id if final_batch else None,
    }


@router.get("/specimen/find/{accession_no}")
def specimen_find(accession_no: str, db: Session = Depends(get_db)):
    accession_no = normalize_accession_input(accession_no)
    order = find_order_by_accession(db, accession_no)
    lookup_accession = order.accession_no if order else accession_no
    arrivals = (
        db.query(SpecimenArrival)
        .filter(SpecimenArrival.accession_no == lookup_accession)
        .order_by(SpecimenArrival.arrived_at.desc())
        .all()
    )
    micro_assignments = (
        db.query(MicroCultureAssignment)
        .filter(MicroCultureAssignment.accession_no == lookup_accession)
        .order_by(MicroCultureAssignment.assigned_at.desc())
        .all()
    )
    tests = []
    if order:
        tests = [
            {
                "test_code": test.test_code,
                "test_name": test.test_name,
                "department_major": test.department_major,
                "aliquot_required": test.aliquot_required,
                "transfer_required": test.transfer_required,
            }
            for test in order.tests
        ]

    return {
        "searched_accession_no": accession_no,
        "accession_no": lookup_accession,
        "order_found": order is not None,
        "arrival_status": "도착" if arrivals else "미도착",
        "patient_name": order.patient_name if order else None,
        "patient_age": order.patient_age if order else None,
        "specimen_name": order.specimen_name if order else None,
        "department_cards": build_department_cards(tests),
        "tests": tests,
        "arrivals": [
            {
                "specimen_category": row.specimen_category,
                "arrived_at": row.arrived_at.isoformat() if row.arrived_at else None,
                "arrived_by": row.arrived_by,
                "workstation_name": row.workstation_name,
                "is_prearrival": row.is_prearrival,
                "is_unregistered": row.is_unregistered,
            }
            for row in arrivals
        ],
        "micro_assignments": [
            {
                "culture_type": row.culture_type,
                "department_major": "미생물",
                "hole_code": row.hole_code,
                "rack_no": row.rack_no,
                "hole_no": row.hole_no,
                "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None,
            }
            for row in micro_assignments
        ],
    }
