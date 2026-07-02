"""지사별 검체 확인 서비스 — PC별 분류코드 선택 → 랙 위치 계산 → 스캔 추적

준비(prepare) 재호출 동작:
  • 동일 분류코드  → 신규 접수번호만 뒤에 추가, 기존 아이템(스캔 완료 포함) 유지
  • 분류코드 변경  → 기존 세션 삭제 후 처음부터 재생성
"""
import json
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import BranchRackItem, BranchRackSession, Order
from app.services.barcode_service import normalize_accession_input

RACK_SIZE = 50


def _sort_key(accno: str) -> int:
    try:
        return int(accno)
    except (ValueError, TypeError):
        return 0


def get_available_branch_codes(db: Session) -> list[str]:
    """현재 DB의 접수번호 앞 2자리로 분류코드 목록 생성"""
    rows = db.query(Order.accession_no).filter(Order.accession_no.isnot(None)).all()
    codes: set[str] = set()
    for (accno,) in rows:
        if accno and len(accno) >= 2:
            codes.add(accno[:2])
    return sorted(codes)


def prepare_branch_rack(
    db: Session,
    workstation_name: str,
    branch_codes: list[str],
    rack_size: int = RACK_SIZE,
) -> dict:
    """선택된 분류코드로 세션 생성/갱신.

    - 동일 분류코드로 재호출: 신규 검체만 뒤에 추가 (기존 스캔 상태 유지)
    - 분류코드 변경 후 호출: 기존 세션 삭제 후 처음부터 생성
    """
    if not workstation_name:
        raise ValueError("PC명을 입력하세요.")
    if not branch_codes:
        raise ValueError("분류코드를 하나 이상 선택하세요.")

    existing = db.query(BranchRackSession).filter(
        BranchRackSession.workstation_name == workstation_name
    ).first()

    if existing:
        existing_codes = sorted(json.loads(existing.branch_codes_json))
        if existing_codes == sorted(branch_codes):
            # 동일 코드 → 신규 검체만 추가
            return _merge_branch_rack(db, existing, branch_codes, rack_size)
        else:
            # 코드 변경 → 기존 세션 삭제 후 신규 생성
            db.delete(existing)
            db.flush()

    return _create_branch_rack(db, workstation_name, branch_codes, rack_size)


def _create_branch_rack(
    db: Session,
    workstation_name: str,
    branch_codes: list[str],
    rack_size: int,
) -> dict:
    """처음부터 세션 생성 (기존 세션 없거나 코드 변경 시)"""
    filters = [Order.accession_no.like(f"{code}%") for code in branch_codes]
    orders = db.query(Order).filter(or_(*filters)).all()
    orders.sort(key=lambda o: _sort_key(o.accession_no))

    session = BranchRackSession(
        workstation_name=workstation_name,
        branch_codes_json=json.dumps(branch_codes, ensure_ascii=False),
        rack_size=rack_size,
        total_items=len(orders),
    )
    db.add(session)
    db.flush()

    items = []
    for idx, order in enumerate(orders):
        sort_no = idx + 1
        items.append(BranchRackItem(
            session_id=session.id,
            accession_no=order.accession_no,
            branch_code=order.accession_no[:2] if len(order.accession_no) >= 2 else "",
            sort_no=sort_no,
            rack_no=(sort_no - 1) // rack_size + 1,
            rack_position=(sort_no - 1) % rack_size + 1,
        ))

    if items:
        db.add_all(items)
    db.commit()

    total_racks = ((len(orders) - 1) // rack_size + 1) if orders else 0
    return {
        "workstation_name": workstation_name,
        "branch_codes": branch_codes,
        "total_items": len(orders),
        "total_racks": total_racks,
        "rack_size": rack_size,
        "added": len(orders),
        "is_new": True,
    }


def _merge_branch_rack(
    db: Session,
    session: BranchRackSession,
    branch_codes: list[str],
    rack_size: int,
) -> dict:
    """기존 세션에 신규 검체만 추가 — 기존 아이템 및 스캔 상태 유지.

    신규 검체는 기존 최대 sort_no 이후로 오름차순 번호를 부여한다.
    이미 물리적 랙에 꽂힌 기존 검체 위치가 변하지 않는다.
    """
    existing_items = (
        db.query(BranchRackItem)
        .filter(BranchRackItem.session_id == session.id)
        .all()
    )
    existing_accnos = {item.accession_no for item in existing_items}

    # 분류코드에 해당하는 전체 접수번호
    filters = [Order.accession_no.like(f"{code}%") for code in branch_codes]
    all_orders = db.query(Order).filter(or_(*filters)).all()

    # 신규 접수번호만 추출
    new_orders = [o for o in all_orders if o.accession_no not in existing_accnos]

    if not new_orders:
        total_racks = ((session.total_items - 1) // rack_size + 1) if session.total_items > 0 else 0
        return {
            "workstation_name": session.workstation_name,
            "branch_codes": branch_codes,
            "total_items": session.total_items,
            "total_racks": total_racks,
            "rack_size": rack_size,
            "added": 0,
            "is_new": False,
        }

    new_orders.sort(key=lambda o: _sort_key(o.accession_no))

    # 기존 sort_no 최대값 이후부터 번호 부여
    max_sort_no = max(item.sort_no for item in existing_items) if existing_items else 0

    new_items = []
    for idx, order in enumerate(new_orders):
        sort_no = max_sort_no + idx + 1
        new_items.append(BranchRackItem(
            session_id=session.id,
            accession_no=order.accession_no,
            branch_code=order.accession_no[:2] if len(order.accession_no) >= 2 else "",
            sort_no=sort_no,
            rack_no=(sort_no - 1) // rack_size + 1,
            rack_position=(sort_no - 1) % rack_size + 1,
        ))

    db.add_all(new_items)
    new_total = session.total_items + len(new_orders)
    session.total_items = new_total
    db.commit()

    total_racks = ((new_total - 1) // rack_size + 1) if new_total > 0 else 0
    return {
        "workstation_name": session.workstation_name,
        "branch_codes": branch_codes,
        "total_items": new_total,
        "total_racks": total_racks,
        "rack_size": rack_size,
        "added": len(new_orders),
        "is_new": False,
    }


def get_session(db: Session, workstation_name: str) -> dict | None:
    """세션 + 전체 아이템 목록 반환 (폴링 및 페이지 초기 로드용)"""
    session = db.query(BranchRackSession).filter(
        BranchRackSession.workstation_name == workstation_name
    ).first()
    if not session:
        return None

    items = (
        db.query(BranchRackItem)
        .filter(BranchRackItem.session_id == session.id)
        .order_by(BranchRackItem.sort_no)
        .all()
    )

    accnos = [item.accession_no for item in items]
    orders_map: dict[str, Order] = {}
    if accnos:
        for o in db.query(Order).filter(Order.accession_no.in_(accnos)).all():
            orders_map[o.accession_no] = o

    scanned_count = sum(1 for item in items if item.scanned)
    branch_codes: list[str] = json.loads(session.branch_codes_json)
    total_racks = ((session.total_items - 1) // session.rack_size + 1) if session.total_items > 0 else 0

    return {
        "workstation_name": session.workstation_name,
        "branch_codes": branch_codes,
        "total_items": session.total_items,
        "total_racks": total_racks,
        "rack_size": session.rack_size,
        "scanned_count": scanned_count,
        "items": [
            {
                "sort_no": item.sort_no,
                "accession_no": item.accession_no,
                "branch_code": item.branch_code,
                "rack_no": item.rack_no,
                "rack_position": item.rack_position,
                "scanned": item.scanned,
                "patient_name": orders_map[item.accession_no].patient_name if item.accession_no in orders_map else None,
                "hospital_name": orders_map[item.accession_no].hospital_name if item.accession_no in orders_map else None,
                "specimen_name": orders_map[item.accession_no].specimen_name if item.accession_no in orders_map else None,
            }
            for item in items
        ],
    }


def scan_branch_rack(
    db: Session,
    raw_accession_no: str,
    workstation_name: str,
    operator_name: str | None = None,
) -> dict:
    """바코드 스캔 처리 → 랙 위치 반환 + 스캔 완료 표시"""
    accession_no = normalize_accession_input(raw_accession_no)

    if not accession_no:
        return {"status": "ERROR", "accession_no": "", "message": "접수번호가 비어 있습니다."}

    session = db.query(BranchRackSession).filter(
        BranchRackSession.workstation_name == workstation_name
    ).first()
    branch_codes: list[str] = json.loads(session.branch_codes_json) if session else []

    order = db.query(Order).filter(Order.accession_no == accession_no).first()
    if not order:
        return {
            "status": "NOT_FOUND",
            "accession_no": accession_no,
            "message": "워크리스트에 없는 검체입니다.",
        }

    item_branch_code = accession_no[:2] if len(accession_no) >= 2 else ""
    if not session or item_branch_code not in branch_codes:
        return {
            "status": "WRONG_CODE",
            "accession_no": accession_no,
            "branch_code": item_branch_code,
            "patient_name": order.patient_name,
            "hospital_name": order.hospital_name,
            "message": f"이 검체는 현재 선택된 분류코드 대상이 아닙니다. 분류코드: {item_branch_code}",
        }

    item = db.query(BranchRackItem).filter(
        BranchRackItem.session_id == session.id,
        BranchRackItem.accession_no == accession_no,
    ).first()

    if not item:
        return {
            "status": "NOT_IN_SESSION",
            "accession_no": accession_no,
            "branch_code": item_branch_code,
            "message": "세션 목록에 없는 검체입니다. 준비 시작을 다시 눌러주세요.",
        }

    already = item.scanned
    item.scanned = True
    item.scanned_at = datetime.now(timezone.utc)
    item.operator_name = operator_name
    item.workstation_name = workstation_name
    db.commit()

    test_names = sorted({t.test_name for t in order.tests})
    specimen_parts = sorted({(t.specimen_name or order.specimen_name or "") for t in order.tests} - {""})
    specimen_name = ", ".join(specimen_parts) if specimen_parts else (order.specimen_name or "")

    return {
        "status": "OK",
        "accession_no": accession_no,
        "branch_code": item.branch_code,
        "sort_no": item.sort_no,
        "rack_no": item.rack_no,
        "rack_position": item.rack_position,
        "patient_name": order.patient_name,
        "patient_age": order.patient_age,
        "hospital_name": order.hospital_name,
        "specimen_name": specimen_name,
        "test_names": test_names,
        "already_scanned": already,
        "message": "이미 스캔된 검체입니다." if already else "OK",
    }
