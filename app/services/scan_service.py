from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Order, ScanLog, SpecimenArrival
from app.services.barcode_service import normalize_accession_input
from app.services.routing_service import build_department_cards


MICRO_DEPARTMENT = "미생물"


def has_arrived(db: Session, accession_no: str) -> bool:
    """도착관리(검체 도착처리) 완료 여부 확인. 조회만(LOOKUP) 은 제외."""
    return (
        db.query(SpecimenArrival)
        .filter(
            SpecimenArrival.accession_no == accession_no,
            SpecimenArrival.specimen_category != "조회만",
        )
        .first()
        is not None
    )


def find_order_by_accession(db: Session, accession_no: str) -> Order | None:
    accession_no = normalize_accession_input(accession_no)
    query = db.query(Order).options(joinedload(Order.tests))
    order = query.filter(Order.accession_no == accession_no).first()
    if order:
        return order
    if len(accession_no) <= 7:
        matches = query.filter(Order.accession_no.like(f"%{accession_no}")).limit(2).all()
        if len(matches) == 1:
            return matches[0]
    return None


def _display_aliquot_required(test, has_micro: bool, has_other_department: bool) -> bool:
    if has_micro and has_other_department:
        return test.department_major != MICRO_DEPARTMENT
    return test.aliquot_required


def _display_transfer_required(test, has_micro: bool, has_other_department: bool) -> bool:
    if has_micro and has_other_department:
        return test.department_major != MICRO_DEPARTMENT
    return test.transfer_required


def _order_payload(order: Order | None) -> tuple[list[dict], list[dict], bool, bool]:
    if not order:
        return [], [], False, False

    departments = {test.department_major for test in order.tests}
    has_micro = MICRO_DEPARTMENT in departments
    has_other_department = len(departments - {MICRO_DEPARTMENT}) > 0
    tests = [
        {
            "test_code": test.test_code,
            "test_name": test.test_name,
            "department_major": test.department_major,
            "aliquot_required": _display_aliquot_required(test, has_micro, has_other_department),
            "transfer_required": _display_transfer_required(test, has_micro, has_other_department),
        }
        for test in order.tests
    ]
    return (
        tests,
        build_department_cards(tests),
        any(test["aliquot_required"] for test in tests),
        any(test["transfer_required"] for test in tests),
    )


def _latest_arrival(db: Session, accession_no: str) -> SpecimenArrival | None:
    return (
        db.query(SpecimenArrival)
        .filter(SpecimenArrival.accession_no == accession_no)
        .order_by(SpecimenArrival.arrived_at.desc())
        .first()
    )


def scan_specimen(
    db: Session,
    accession_no: str,
    specimen_category: str | None,
    client_name: str | None,
    operator_name: str | None = None,
    workstation_name: str | None = None,
) -> dict:
    accession_no = normalize_accession_input(accession_no)
    category = (specimen_category or "").strip()
    order = find_order_by_accession(db, accession_no)

    lookup_only = not category or category == "조회만"
    arrived = False
    status = "LOOKUP"
    message = "조회만 수행했습니다."

    if not lookup_only:
        try:
            arrival = SpecimenArrival(
                order_id=order.id if order else None,
                accession_no=accession_no,
                specimen_category=category,
                arrived_by=operator_name,
                workstation_name=workstation_name,
                is_prearrival=order is None,
                is_unregistered=False,
            )
            db.add(arrival)
            db.flush()
            arrived = True
            status = "ARRIVED" if order else "PREARRIVAL"
            message = "도착처리되었습니다." if order else "접수리스트에 없어 선도착으로 저장했습니다."
        except IntegrityError:
            db.rollback()
            status = "DUPLICATE"
            message = "이미 같은 카테고리로 도착처리된 검체입니다."

        db.add(
            ScanLog(
                accession_no=accession_no,
                scan_type="specimen",
                specimen_category=category,
                result_status=status,
                message=message,
                client_name=client_name,
                operator_name=operator_name,
                workstation_name=workstation_name,
            )
        )

    tests, cards, aliquot, transfer = _order_payload(order)
    db.commit()
    latest_arrival = _latest_arrival(db, accession_no)

    return {
        "accession_no": accession_no,
        "status": status,
        "message": message,
        "order_found": order is not None,
        "arrived": arrived,
        "patient_name": order.patient_name if order else None,
        "patient_age": order.patient_age if order else None,
        "specimen_name": order.specimen_name if order else None,
        "tests": tests,
        "department_cards": cards,
        "aliquot_required": aliquot,
        "transfer_required": transfer,
        "arrival_checked_at": latest_arrival.arrived_at.isoformat() if latest_arrival and latest_arrival.arrived_at else None,
        "arrival_checked_by": latest_arrival.arrived_by if latest_arrival else None,
        "arrival_workstation": latest_arrival.workstation_name if latest_arrival else None,
    }
