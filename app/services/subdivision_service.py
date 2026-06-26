from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DepartmentSubcategoryAssignment, DepartmentSubcategoryRule, MicroCultureAssignment, Order, OrderTest, ScanLog
from app.services.culture_matcher import infer_micro_culture_types, is_matching_micro_culture, normalize_text
from app.services.scan_service import has_arrived


def _filter_tests_for_row(
    tests_with_dept: list[tuple[str, str]],
    specimen_name: str | None,
    department_name: str,
    subcategory: str,
) -> list[str]:
    """소분류 현황 테이블: 해당 학부·소분류에 맵핑된 검사명만 반환"""
    # 1단계: 담당 학부 소속 검사만 선별
    dept_tests = [name for name, dept in tests_with_dept if dept == department_name]

    if subcategory in MICRO_SUBCATEGORIES:
        # 미생물: 배양 타입까지 매칭하여 추가 필터
        culture_matched = [
            name for name in dept_tests
            if subcategory in infer_micro_culture_types([name], specimen_name)
        ]
        # 개별 매칭이 없으면 학부 전체 검사 표시 (fallback)
        return culture_matched if culture_matched else dept_tests

    return dept_tests


MICRO_SUBCATEGORIES = {
    "Urine culture",
    "Sputum culture",
    "Stool/Rectal culture",
    "CRE culture",
    "VRE culture",
    "보건증",
    "Tip culture",
    "Bronchial washing culture",
    "Other culture",
}


def _location_code(prefix: str, sequence_no: int) -> tuple[int, int, str]:
    rack_no = ((sequence_no - 1) // 100) + 1
    hole_no = ((sequence_no - 1) % 100) + 1
    return rack_no, hole_no, f"{prefix}-R{rack_no:02d}-H{hole_no:03d}"


def _has_matching_subcategory_test(db: Session, accession_no: str, subcategory: str) -> tuple[bool, list[str]]:
    order = db.query(Order).filter(Order.accession_no == accession_no).first()
    if not order:
        return False, []
    tests = db.query(OrderTest).filter(OrderTest.order_id == order.id).order_by(OrderTest.id.asc()).all()
    names = [test.test_name for test in tests]
    if subcategory in MICRO_SUBCATEGORIES:
        if order and is_matching_micro_culture(names, order.specimen_name, subcategory):
            return True, names
        return False, names
    normalized_subcategory = normalize_text(subcategory)
    if any(normalized_subcategory and normalized_subcategory in normalize_text(name) for name in names):
        return True, names
    return False, names


def _assignment_matches_tests(order: Order | None, test_names: list[str], subcategory: str) -> bool:
    if not order or not test_names:
        return True
    if subcategory in MICRO_SUBCATEGORIES:
        return is_matching_micro_culture(test_names, order.specimen_name, subcategory)
    normalized_subcategory = normalize_text(subcategory)
    return any(normalized_subcategory and normalized_subcategory in normalize_text(name) for name in test_names)


def assign_department_subcategory(
    db: Session,
    accession_no: str,
    department_name: str,
    subcategory: str,
    client_name: str | None,
    operator_name: str | None = None,
    workstation_name: str | None = None,
) -> dict:
    accession_no = accession_no.strip()
    department_name = department_name.strip()
    subcategory = subcategory.strip()

    # ── 도착관리 선행 검증 ──────────────────────────────────────────────────
    if not has_arrived(db, accession_no):
        message = (
            f"[{accession_no}] 도착관리가 완료되지 않은 검체입니다. "
            "스캔 페이지에서 도착처리를 먼저 시행하세요."
        )
        db.add(
            ScanLog(
                accession_no=accession_no,
                scan_type="department_subcategory",
                culture_type=f"{department_name}:{subcategory}",
                result_status="NO_ARRIVAL",
                message=message,
                client_name=client_name,
                operator_name=operator_name,
                workstation_name=workstation_name,
            )
        )
        db.commit()
        return {"status": "NO_ARRIVAL", "message": message, "assignment": None}
    # ────────────────────────────────────────────────────────────────────────

    matched, test_names = _has_matching_subcategory_test(db, accession_no, subcategory)
    if not matched:
        listed = ", ".join(test_names) or "검사항목 없음"
        order = db.query(Order).filter(Order.accession_no == accession_no).first()
        if subcategory in MICRO_SUBCATEGORIES:
            allowed = ", ".join(infer_micro_culture_types(test_names, order.specimen_name if order else None)) or "자동 분류 불가"
            message = f"{accession_no} 검체는 {subcategory} 대상이 아닙니다. 권장 소분류: {allowed}. 등록검사: {listed}"
        else:
            message = f"{accession_no} 검체에는 {subcategory} 검사항목이 없습니다. 선택 항목을 확인하세요. 등록검사: {listed}"
        db.add(
            ScanLog(
                accession_no=accession_no,
                scan_type="department_subcategory",
                culture_type=f"{department_name}:{subcategory}",
                result_status="SUBCATEGORY_MISMATCH",
                message=message,
                client_name=client_name,
                operator_name=operator_name,
                workstation_name=workstation_name,
            )
        )
        db.commit()
        return {"status": "SUBCATEGORY_MISMATCH", "message": message, "assignment": None}

    existing = (
        db.query(DepartmentSubcategoryAssignment)
        .filter(
            DepartmentSubcategoryAssignment.accession_no == accession_no,
            DepartmentSubcategoryAssignment.department_name == department_name,
            DepartmentSubcategoryAssignment.subcategory == subcategory,
        )
        .first()
    )
    if existing:
        db.add(
            ScanLog(
                accession_no=accession_no,
                scan_type="department_subcategory",
                culture_type=subcategory,
                result_status="DUPLICATE",
                message=f"이미 발급된 위치 번호: {existing.location_code}",
                client_name=client_name,
                operator_name=operator_name,
                workstation_name=workstation_name,
            )
        )
        db.commit()
        return {"status": "DUPLICATE", "message": "이미 발급된 검체입니다.", "assignment": _assignment_dict(existing)}

    rule = (
        db.query(DepartmentSubcategoryRule)
        .filter(
            DepartmentSubcategoryRule.department_name == department_name,
            DepartmentSubcategoryRule.subcategory == subcategory,
            DepartmentSubcategoryRule.enabled.is_(True),
        )
        .with_for_update()
        .first()
    )
    if not rule:
        raise ValueError("사용 가능한 소분류 항목이 아닙니다.")

    sequence_no = rule.next_sequence
    rack_no, hole_no, code = _location_code(rule.prefix, sequence_no)
    assignment = DepartmentSubcategoryAssignment(
        accession_no=accession_no,
        department_name=department_name,
        subcategory=subcategory,
        prefix=rule.prefix,
        sequence_no=sequence_no,
        rack_no=rack_no,
        hole_no=hole_no,
        location_code=code,
        assigned_by=operator_name,
        workstation_name=workstation_name,
    )
    db.add(assignment)
    rule.next_sequence += 1
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return assign_department_subcategory(
            db,
            accession_no,
            department_name,
            subcategory,
            client_name,
            operator_name,
            workstation_name,
        )

    db.add(
        ScanLog(
            accession_no=accession_no,
            scan_type="department_subcategory",
            culture_type=f"{department_name}:{subcategory}",
            result_status="ASSIGNED",
            message=f"위치 번호 발급: {code}",
            client_name=client_name,
            operator_name=operator_name,
            workstation_name=workstation_name,
        )
    )
    db.commit()
    return {"status": "ASSIGNED", "message": "위치 번호가 발급되었습니다.", "assignment": _assignment_dict(assignment)}


def combined_assignments(db: Session, from_date=None) -> list[dict]:
    orders = {row.accession_no: row for row in db.query(Order).all()}
    order_sort = {accession_no: order.id for accession_no, order in orders.items()}
    order_ids = [order.id for order in orders.values()]

    # (test_name, department_major) 튜플로 저장 — 학부별 필터링에 사용
    tests_full_by_order: dict[int, list[tuple[str, str]]] = {order_id: [] for order_id in order_ids}
    if order_ids:
        for test in db.query(OrderTest).filter(OrderTest.order_id.in_(order_ids)).order_by(OrderTest.id.asc()).all():
            tests_full_by_order.setdefault(test.order_id, []).append((test.test_name, test.department_major))

    def _names(order_id: int) -> list[str]:
        return [n for n, _ in tests_full_by_order.get(order_id, [])]

    micro_q = db.query(MicroCultureAssignment)
    dept_q  = db.query(DepartmentSubcategoryAssignment)
    if from_date is not None:
        micro_q = micro_q.filter(MicroCultureAssignment.assigned_at >= from_date)
        dept_q  = dept_q.filter(DepartmentSubcategoryAssignment.assigned_at >= from_date)

    micro_rows = (
        micro_q
        .order_by(MicroCultureAssignment.assigned_at.asc(), MicroCultureAssignment.id.asc())
        .limit(2000)
        .all()
    )
    dept_rows = (
        dept_q
        .order_by(DepartmentSubcategoryAssignment.assigned_at.asc(), DepartmentSubcategoryAssignment.id.asc())
        .limit(2000)
        .all()
    )
    rows = []
    for row in micro_rows:
        order = orders.get(row.accession_no)
        test_names = _names(order.id) if order else []
        if not _assignment_matches_tests(order, test_names, row.culture_type):
            continue
        rows.append({
            "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None,
            "accession_no": row.accession_no,
            "department_name": "미생물",
            "subcategory": row.culture_type,
            "location_code": row.hole_code,
            "sequence_no": row.sequence_no,
            "worklist_order": order_sort.get(row.accession_no),
        })
    for row in dept_rows:
        order = orders.get(row.accession_no)
        test_names = _names(order.id) if order else []
        if not _assignment_matches_tests(order, test_names, row.subcategory):
            continue
        rows.append(_assignment_dict(row))
    for row in rows:
        row["worklist_order"] = row.get("worklist_order") or order_sort.get(row["accession_no"])
        order = orders.get(row["accession_no"])
        row["patient_name"] = order.patient_name if order else None
        row["patient_age"] = order.patient_age if order else None
        row["patient_id"] = order.patient_id if order else None
        row["hospital_name"] = order.hospital_name if order else None
        row["specimen_name"] = order.specimen_name if order else None
        row["accession_date"] = order.accession_date if order else None
        # ── 담당 학부·소분류에 맵핑된 검사명만 표시 ──────────────────────────
        row["test_names"] = _filter_tests_for_row(
            tests_full_by_order.get(order.id, []) if order else [],
            order.specimen_name if order else None,
            row["department_name"],
            row["subcategory"],
        )
        # ────────────────────────────────────────────────────────────────────
        row["group_key"] = f"{row['department_name']}|{row['subcategory']}"

    sorted_rows = sorted(
        rows,
        key=lambda item: (
            item["department_name"],
            item["subcategory"],
            item["worklist_order"] is None,
            item["worklist_order"] or 0,
            item["accession_no"],
            item["assigned_at"] or "",
        ),
    )
    group_counts: dict[str, int] = {}
    for index, row in enumerate(sorted_rows, start=1):
        group_key = row["group_key"]
        group_counts[group_key] = group_counts.get(group_key, 0) + 1
        row["scan_no"] = index
        row["group_item_no"] = group_counts[group_key]
        row["page_no"] = ((row["group_item_no"] - 1) // 30) + 1
        row["page_item_no"] = ((row["group_item_no"] - 1) % 30) + 1
    return sorted_rows


def _assignment_dict(item: DepartmentSubcategoryAssignment) -> dict:
    return {
        "assigned_at": item.assigned_at.isoformat() if item.assigned_at else None,
        "accession_no": item.accession_no,
        "department_name": item.department_name,
        "subcategory": item.subcategory,
        "location_code": item.location_code,
        "sequence_no": item.sequence_no,
        "worklist_order": None,
    }
