from datetime import date, datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import CultureRule, MicroCultureAssignment, MicroCulturePlan, Order, OrderTest, ScanLog, SpecimenArrival
from app.services.culture_matcher import infer_culture_for_test, infer_micro_culture_types, normalize_text
from app.services.scan_service import MICRO_DEPARTMENT, _order_payload, find_order_by_accession, has_arrived

RACK_SIZE = 50  # 50칸 스폰지랙


def _today_start() -> datetime:
    """오늘 KST 00:00 → UTC naive"""
    d = date.today()
    return datetime(d.year, d.month, d.day) - timedelta(hours=9)


SHIFT_HOUR = 19  # 출근 기준 시각 (KST)


def _shift_start() -> datetime:
    """출근 기준(KST 19:00) 시작 시각 → UTC naive
    현재 KST 19시 이전이면 전날 19시, 이후면 오늘 19시"""
    now_kst = datetime.now()
    today = now_kst.date()
    today_19 = datetime(today.year, today.month, today.day, SHIFT_HOUR, 0)
    if now_kst >= today_19:
        shift_kst = today_19
    else:
        yesterday = today - timedelta(days=1)
        shift_kst = datetime(yesterday.year, yesterday.month, yesterday.day, SHIFT_HOUR, 0)
    return shift_kst - timedelta(hours=9)  # KST → UTC


# ──────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _hole_code(prefix: str, lis_order: int) -> tuple[int, int, str]:
    """기존 100칸 기준 hole 코드 (하위 호환)"""
    rack_no = ((lis_order - 1) // 100) + 1
    hole_no = ((lis_order - 1) % 100) + 1
    date_str = date.today().strftime("%m%d")
    return rack_no, hole_no, f"{date_str}-{prefix}-R{rack_no:02d}-H{hole_no:03d}"


def _rack_code(prefix: str, culture_order: int, rack_size: int = RACK_SIZE) -> tuple[int, int, str]:
    """스폰지랙 기준 위치 코드 계산 (기본 50칸, 100칸 선택 가능)
    rack_no      = ((culture_order - 1) // rack_size) + 1
    rack_position = ((culture_order - 1) % rack_size) + 1
    code          = {prefix}-R{rack_no:02d}-P{rack_position:03d}
    """
    rack_no  = ((culture_order - 1) // rack_size) + 1
    rack_pos = ((culture_order - 1) % rack_size) + 1
    code = f"{prefix}-R{rack_no:02d}-P{rack_pos:03d}"
    return rack_no, rack_pos, code


def _micro_context(db: Session, accession_no: str) -> dict:
    order = find_order_by_accession(db, accession_no)
    tests, cards, aliquot, transfer = _order_payload(order)
    departments = {test["department_major"] for test in tests}
    other_departments = sorted(departments - {MICRO_DEPARTMENT})
    has_micro = MICRO_DEPARTMENT in departments
    status = "UNREGISTERED"
    headline = "접수리스트에 없는 검체입니다"
    warning_level = "danger"
    if order and has_micro and other_departments:
        status, headline, warning_level = "SHARED", "공유검체입니다. 미생물 처리 후 다른 학부 전달이 필요합니다", "warning"
    elif order and has_micro:
        status, headline, warning_level = "MICRO_ONLY", "미생물 검체입니다", "success"
    elif order:
        status, headline, warning_level = "WRONG_DEPARTMENT", "미생물 검사가 없는 검체입니다. 해당 학부로 보내야 합니다", "danger"
    return {
        "accession_no": accession_no,
        "order_found": order is not None,
        "patient_name": order.patient_name if order else None,
        "patient_age": order.patient_age if order else None,
        "specimen_name": order.specimen_name if order else None,
        "tests": tests,
        "allowed_culture_types": infer_micro_culture_types(
            [t["test_name"] for t in tests], order.specimen_name if order else None
        ),
        "department_cards": cards,
        "aliquot_required": aliquot,
        "transfer_required": transfer,
        "has_micro": has_micro,
        "other_departments": other_departments,
        "routing_status": status,
        "routing_headline": headline,
        "warning_level": warning_level,
    }


def _scan_log(db, accession_no, culture_type, status, message, client_name, operator_name, workstation_name):
    db.add(ScanLog(
        accession_no=accession_no,
        scan_type="micro_culture",
        culture_type=culture_type,
        result_status=status,
        message=message,
        client_name=client_name,
        operator_name=operator_name,
        workstation_name=workstation_name,
    ))


# ──────────────────────────────────────────────────────────────────────────────
# 메인 스캔 함수 — plan 기반
# ──────────────────────────────────────────────────────────────────────────────

def assign_culture_hole(
    db: Session,
    accession_no: str,
    culture_type: str,
    client_name: str | None,
    operator_name: str | None = None,
    workstation_name: str | None = None,
) -> dict:
    accession_no = accession_no.strip()

    # 1. 도착관리 선행 검증
    if not has_arrived(db, accession_no):
        message = (
            f"[{accession_no}] 도착관리가 완료되지 않은 검체입니다. "
            "스캔 페이지에서 도착처리를 먼저 시행하세요."
        )
        _scan_log(db, accession_no, culture_type, "NO_ARRIVAL", message, client_name, operator_name, workstation_name)
        db.commit()
        return {"status": "NO_ARRIVAL", "message": message, "assignment": None, "routing": None}

    # 2. 예정 목록(plan) 조회
    plan = (
        db.query(MicroCulturePlan)
        .filter(
            MicroCulturePlan.accession_no == accession_no,
            MicroCulturePlan.culture_type == culture_type,
        )
        .first()
    )

    if not plan:
        # 이 검체는 선택한 culture type 예정 목록에 없음
        order = find_order_by_accession(db, accession_no)
        test_names = [t.test_name for t in (order.tests if order else [])]
        allowed = infer_micro_culture_types(test_names, order.specimen_name if order else None)
        allowed_str = ", ".join(allowed) or "해당 없음"
        message = (
            f"[{accession_no}]는 {culture_type} 소분류 대상이 아닙니다. "
            f"권장 소분류: {allowed_str}"
        )
        _scan_log(db, accession_no, culture_type, "PLAN_MISMATCH", message, client_name, operator_name, workstation_name)
        db.commit()
        context = _micro_context(db, accession_no)
        return {"status": "PLAN_MISMATCH", "message": message, "assignment": None, "routing": context}

    # 3. 이미 완료된 검체
    if plan.status == "DONE":
        existing = (
            db.query(MicroCultureAssignment)
            .filter(
                MicroCultureAssignment.accession_no == accession_no,
                MicroCultureAssignment.culture_type == culture_type,
            )
            .first()
        )
        _scan_log(db, accession_no, culture_type, "DUPLICATE",
                  f"이미 발급된 Hole 번호: {existing.hole_code if existing else '-'}",
                  client_name, operator_name, workstation_name)
        db.commit()
        return {
            "status": "DUPLICATE",
            "message": "이미 발급된 검체입니다.",
            "assignment": _assignment_dict(existing) if existing else None,
            "routing": _micro_context(db, accession_no),
        }

    # 4. CultureRule 조회 (prefix 확인)
    rule = (
        db.query(CultureRule)
        .filter(CultureRule.culture_type == culture_type, CultureRule.enabled.is_(True))
        .first()
    )
    if not rule:
        raise ValueError("사용 가능한 culture_type이 아닙니다.")

    # 5. LIS순으로 Hole 번호 결정 (순번은 plan.lis_order 고정)
    rack_no, hole_no, code = _hole_code(rule.prefix, plan.lis_order)

    assignment = MicroCultureAssignment(
        accession_no=accession_no,
        culture_type=culture_type,
        prefix=rule.prefix,
        sequence_no=plan.lis_order,
        rack_no=rack_no,
        hole_no=hole_no,
        hole_code=code,
    )
    db.add(assignment)

    # 6. Plan 상태 → DONE
    plan.status = "DONE"
    plan.assignment_id = assignment.id

    _scan_log(db, accession_no, culture_type, "ASSIGNED",
              f"Hole 번호 발급: {code} (LIS순 {plan.lis_order})",
              client_name, operator_name, workstation_name)
    try:
        db.commit()
    except IntegrityError:
        # 다른 PC가 동시에 같은 검체를 먼저 처리한 경우 → DUPLICATE로 반환
        db.rollback()
        existing = (
            db.query(MicroCultureAssignment)
            .filter(
                MicroCultureAssignment.accession_no == accession_no,
                MicroCultureAssignment.culture_type == culture_type,
            )
            .first()
        )
        _scan_log(db, accession_no, culture_type, "DUPLICATE",
                  f"동시 처리 감지 — 이미 발급된 Hole 번호: {existing.hole_code if existing else '-'}",
                  client_name, operator_name, workstation_name)
        db.commit()
        return {
            "status": "DUPLICATE",
            "message": "다른 PC에서 동시에 처리되었습니다. 이미 발급된 번호를 확인하세요.",
            "assignment": _assignment_dict(existing) if existing else None,
            "routing": _micro_context(db, accession_no),
        }

    context = _micro_context(db, accession_no)
    return {
        "status": "ASSIGNED",
        "message": "Hole 번호가 발급되었습니다.",
        "assignment": _assignment_dict(assignment),
        "lis_order": plan.lis_order,
        "routing": context,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 예정 목록 / 스캔 완료 목록 조회
# ──────────────────────────────────────────────────────────────────────────────

def get_culture_plan_list(db: Session, culture_type: str) -> dict:
    """선택한 culture_type의 오늘 예정 목록(PENDING) + 오늘 완료 목록(DONE) 반환"""
    plans = (
        db.query(MicroCulturePlan)
        .filter(
            MicroCulturePlan.culture_type == culture_type,
            MicroCulturePlan.planned_at >= _today_start(),   # 오늘 날짜 필터
        )
        .order_by(MicroCulturePlan.lis_order.asc())
        .all()
    )

    # 접수번호 → 주문 정보 맵
    accession_nos = [p.accession_no for p in plans]
    orders = {
        o.accession_no: o
        for o in db.query(Order).filter(Order.accession_no.in_(accession_nos)).all()
    }
    order_ids = [o.id for o in orders.values()]
    tests_by_order: dict[int, list[str]] = {}
    for t in db.query(OrderTest).filter(OrderTest.order_id.in_(order_ids)).all():
        tests_by_order.setdefault(t.order_id, []).append(t.test_name)

    # 완료된 항목의 assignment 정보 (오늘 스캔된 것만)
    done_accnos = [p.accession_no for p in plans if p.status == "DONE"]
    assignments = {
        a.accession_no: a
        for a in db.query(MicroCultureAssignment)
        .filter(
            MicroCultureAssignment.accession_no.in_(done_accnos),
            MicroCultureAssignment.culture_type == culture_type,
            MicroCultureAssignment.assigned_at >= _today_start(),
        )
        .all()
    }

    pending, done = [], []
    scan_no = 0
    for plan in plans:
        order = orders.get(plan.accession_no)
        all_tests = tests_by_order.get(order.id, []) if order else []
        specimen = order.specimen_name if order else None

        # 해당 culture type에 매핑되는 검사명만 필터
        matched_tests = [
            name for name in all_tests
            if infer_culture_for_test(name, specimen) == culture_type
        ]
        # Other culture 는 culture/배양 포함 전체 매핑 안된 검사
        if not matched_tests and culture_type == "Other culture":
            matched_tests = [
                name for name in all_tests
                if "culture" in normalize_text(name) or "배양" in normalize_text(name)
            ]
        display_tests = matched_tests if matched_tests else all_tests

        row = {
            "accession_no": plan.accession_no,
            "lis_order": plan.lis_order,
            "status": plan.status,
            "patient_name": order.patient_name if order else None,
            "patient_age": order.patient_age if order else None,
            "hospital_name": order.hospital_name if order else None,
            "specimen_name": order.specimen_name if order else None,
            "test_names": display_tests,
            "hole_code": None,
        }
        if plan.status == "DONE":
            scan_no += 1
            asn = assignments.get(plan.accession_no)
            row["hole_code"] = asn.hole_code if asn else None
            row["rack_no"] = asn.rack_no if asn else None
            row["rack_position"] = asn.hole_no if asn else None   # hole_no 필드가 rack_position 저장
            row["assigned_at"] = asn.assigned_at.isoformat() if asn and asn.assigned_at else None
            row["scan_order"] = scan_no
            done.append(row)
        else:
            pending.append(row)

    # 스캔 완료 목록은 LIS순으로 유지 (스캔순은 assigned_at 기준 재정렬)
    done_sorted_by_scan = sorted(
        done,
        key=lambda r: r.get("assigned_at") or "",
    )
    for i, r in enumerate(done_sorted_by_scan, 1):
        r["scan_order"] = i

    total = len(plans)
    done_count = len(done)
    pending_count = total - done_count
    return {
        "culture_type": culture_type,
        "total": total,
        "done": done_count,
        "pending": pending_count,
        "pending_list": pending[:30],    # 화면 표시용: 최대 30개
        "pending_total": pending_count,  # 실제 남은 건수 (배지 표시용)
        "done_list": done_sorted_by_scan,
    }


def _assignment_dict(item: MicroCultureAssignment) -> dict:
    return {
        "accession_no": item.accession_no,
        "culture_type": item.culture_type,
        "prefix": item.prefix,
        "sequence_no": item.sequence_no,
        "rack_no": item.rack_no,
        "hole_no": item.hole_no,
        "hole_code": item.hole_code,
        "assigned_at": item.assigned_at.isoformat() if item.assigned_at else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 자동 소분류 스캔 — culture_type 선택 없이 자동 판정
# ──────────────────────────────────────────────────────────────────────────────

def auto_assign_culture_hole(
    db: Session,
    accession_no: str,
    client_name: str | None,
    operator_name: str | None = None,
    workstation_name: str | None = None,
    rack_size: int = RACK_SIZE,
) -> dict:
    """
    검체 스캔 → culture_type 자동 판정 → 스폰지랙 위치 배정.
    rack_size: 50 또는 100 (칸 수, 기본 50).
    도착관리 선행 검증 없음 (수기 확인 기준 업무 방식).
    """
    accession_no = accession_no.strip()

    # 1. 주문 조회
    order = find_order_by_accession(db, accession_no)
    if not order:
        msg = "접수리스트에 없는 검체입니다."
        _scan_log(db, accession_no, None, "UNREGISTERED", msg, client_name, operator_name, workstation_name)
        db.commit()
        return {"status": "UNREGISTERED", "message": msg}

    test_names = [t.test_name for t in order.tests]
    specimen_name = order.specimen_name

    def _base():
        return {
            "accession_no": accession_no,
            "patient_name": order.patient_name,
            "patient_age": order.patient_age,
            "hospital_name": order.hospital_name,
            "specimen_name": specimen_name,
            "test_names": test_names,
        }

    # 2. culture_type 자동 판정
    culture_types = infer_micro_culture_types(test_names, specimen_name)

    if not culture_types:
        departments = {t.department_major for t in order.tests}
        if MICRO_DEPARTMENT not in departments:
            msg = "미생물 소분류 대상이 아닙니다."
            status = "WRONG_DEPARTMENT"
        else:
            msg = "자동 소분류를 찾을 수 없습니다. 검사명과 검체명을 확인하세요."
            status = "NO_CULTURE_MATCH"
        _scan_log(db, accession_no, None, status, msg, client_name, operator_name, workstation_name)
        db.commit()
        return {"status": status, "message": msg, **_base()}

    # 복수 소분류 시 우선 처리 순서: 산전 GBS 배양검사 → 나머지는 수동
    PRIORITY_AUTO = ["산전 GBS 배양검사"]

    multi_culture_warning: str | None = None
    if len(culture_types) > 1:
        priority_match = next((ct for ct in PRIORITY_AUTO if ct in culture_types), None)
        if priority_match:
            culture_type = priority_match
            multi_culture_warning = (
                f"복수 소분류 대상입니다 ({', '.join(culture_types)}) — "
                f"{priority_match}(으)로 자동 처리됩니다."
            )
            _scan_log(db, accession_no, culture_type, "MULTI_CULTURE_AUTO",
                      multi_culture_warning, client_name, operator_name, workstation_name)
        else:
            msg = f"복수 소분류 대상입니다. 확인 필요: {', '.join(culture_types)}"
            _scan_log(db, accession_no, None, "MULTI_CULTURE", msg, client_name, operator_name, workstation_name)
            db.commit()
            return {"status": "MULTI_CULTURE", "message": msg, "culture_types": culture_types, **_base()}
    else:
        culture_type = culture_types[0]

    # 3. 예정 목록(plan) 조회
    plan = (
        db.query(MicroCulturePlan)
        .filter(
            MicroCulturePlan.accession_no == accession_no,
            MicroCulturePlan.culture_type == culture_type,
        )
        .first()
    )

    if not plan:
        msg = "예정 목록에 없습니다. 접수리스트를 다시 업로드하세요."
        _scan_log(db, accession_no, culture_type, "NOT_IN_PLAN", msg, client_name, operator_name, workstation_name)
        db.commit()
        return {"status": "NOT_IN_PLAN", "message": msg, "culture_type": culture_type, **_base()}

    # 4. 이미 완료된 검체
    if plan.status == "DONE":
        existing = (
            db.query(MicroCultureAssignment)
            .filter(
                MicroCultureAssignment.accession_no == accession_no,
                MicroCultureAssignment.culture_type == culture_type,
            )
            .first()
        )
        rack_no = existing.rack_no if existing else None
        rack_pos = existing.hole_no if existing else None
        dup_msg = (
            f"이미 처리된 검체입니다. "
            f"{culture_type} {rack_no}번 랙 {rack_pos}번 칸"
        )
        _scan_log(db, accession_no, culture_type, "DUPLICATE", dup_msg, client_name, operator_name, workstation_name)
        db.commit()
        matched = [n for n in test_names if infer_culture_for_test(n, specimen_name) == culture_type] or test_names
        return {
            "status": "DUPLICATE",
            "message": dup_msg,
            "culture_type": culture_type,
            "culture_order": plan.lis_order,
            "rack_no": rack_no,
            "rack_position": rack_pos,
            "hole_code": existing.hole_code if existing else None,
            "accession_no": accession_no,
            "patient_name": order.patient_name,
            "patient_age": order.patient_age,
            "hospital_name": order.hospital_name,
            "test_names": matched,
            "specimen_name": specimen_name,
        }

    # 5. CultureRule 조회 (prefix)
    rule = (
        db.query(CultureRule)
        .filter(CultureRule.culture_type == culture_type, CultureRule.enabled.is_(True))
        .first()
    )
    prefix = rule.prefix if rule else culture_type[0].upper()

    # 6. 랙 위치 계산 (선택된 rack_size 적용)
    rack_no, rack_pos, code = _rack_code(prefix, plan.lis_order, rack_size)

    # 7. Assignment 생성
    assignment = MicroCultureAssignment(
        accession_no=accession_no,
        culture_type=culture_type,
        prefix=prefix,
        sequence_no=plan.lis_order,
        rack_no=rack_no,
        hole_no=rack_pos,
        hole_code=code,
    )
    db.add(assignment)

    # 8. Plan → DONE
    plan.status = "DONE"
    plan.assignment_id = assignment.id

    matched = [n for n in test_names if infer_culture_for_test(n, specimen_name) == culture_type] or test_names

    _scan_log(
        db, accession_no, culture_type, "ASSIGNED",
        f"{culture_type} {rack_no}번 랙 {rack_pos}번 칸 ({code})",
        client_name, operator_name, workstation_name,
    )

    # ── 누락검체 연동: SpecimenArrival이 없으면 자동 생성 (누락목록에서 제거) ──
    existing_arrival = (
        db.query(SpecimenArrival)
        .filter(SpecimenArrival.accession_no == accession_no)
        .first()
    )
    if not existing_arrival:
        db.add(SpecimenArrival(
            accession_no=accession_no,
            order_id=order.id,
            specimen_category="Other",
            arrived_by=operator_name,
            workstation_name=workstation_name,
            is_prearrival=False,
            is_unregistered=False,
        ))

    try:
        db.commit()
    except IntegrityError:
        # 다른 PC가 동시에 같은 검체를 먼저 처리한 경우 → DUPLICATE로 반환
        db.rollback()
        existing = (
            db.query(MicroCultureAssignment)
            .filter(
                MicroCultureAssignment.accession_no == accession_no,
                MicroCultureAssignment.culture_type == culture_type,
            )
            .first()
        )
        _scan_log(db, accession_no, culture_type, "DUPLICATE",
                  f"동시 처리 감지 — 이미 발급된 위치: {existing.hole_code if existing else '-'}",
                  client_name, operator_name, workstation_name)
        db.commit()
        dup_rack = existing.rack_no if existing else None
        dup_pos  = existing.hole_no if existing else None
        return {
            "status": "DUPLICATE",
            "message": f"다른 PC에서 동시에 처리되었습니다. {culture_type} {dup_rack}번 랙 {dup_pos}번 칸",
            "culture_type": culture_type,
            "culture_order": plan.lis_order,
            "rack_no": dup_rack,
            "rack_position": dup_pos,
            "hole_code": existing.hole_code if existing else None,
            "accession_no": accession_no,
            "patient_name": order.patient_name,
            "patient_age": order.patient_age,
            "hospital_name": order.hospital_name,
            "test_names": matched,
            "specimen_name": specimen_name,
        }

    base_msg = f"{culture_type}  {rack_no}번 랙 / {rack_pos}번 칸입니다."
    return {
        "status": "ASSIGNED",
        "message": base_msg,
        "multi_culture_warning": multi_culture_warning,
        "culture_types": culture_types if multi_culture_warning else None,
        "culture_type": culture_type,
        "culture_order": plan.lis_order,
        "rack_no": rack_no,
        "rack_position": rack_pos,
        "hole_code": code,
        "accession_no": accession_no,
        "patient_name": order.patient_name,
        "patient_age": order.patient_age,
        "hospital_name": order.hospital_name,
        "test_names": matched,
        "specimen_name": specimen_name,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 오늘 전체 미생물 처리 목록 (작업 목록 표시용)
# ──────────────────────────────────────────────────────────────────────────────

def get_today_micro_assignments(db: Session) -> list[dict]:
    """오늘 처리된 모든 culture_type의 assignment 목록 — 스캔 작업 목록용"""
    assignments = (
        db.query(MicroCultureAssignment)
        .filter(MicroCultureAssignment.assigned_at >= _shift_start())
        .order_by(MicroCultureAssignment.assigned_at.asc())
        .all()
    )
    if not assignments:
        return []

    accession_nos = list({a.accession_no for a in assignments})
    orders = {
        o.accession_no: o
        for o in db.query(Order).filter(Order.accession_no.in_(accession_nos)).all()
    }
    order_ids = [o.id for o in orders.values()]
    tests_by_order: dict[int, list[str]] = {}
    for t in db.query(OrderTest).filter(OrderTest.order_id.in_(order_ids)).all():
        tests_by_order.setdefault(t.order_id, []).append(t.test_name)

    result = []
    for i, asn in enumerate(assignments, 1):
        order = orders.get(asn.accession_no)
        all_tests = tests_by_order.get(order.id, []) if order else []
        specimen = order.specimen_name if order else None
        matched = [
            n for n in all_tests
            if infer_culture_for_test(n, specimen) == asn.culture_type
        ] or all_tests

        result.append({
            "scan_order": i,
            "culture_type": asn.culture_type,
            "culture_order": asn.sequence_no,
            "rack_no": asn.rack_no,
            "rack_position": asn.hole_no,
            "hole_code": asn.hole_code,
            "accession_no": asn.accession_no,
            "patient_name": order.patient_name if order else None,
            "patient_age": order.patient_age if order else None,
            "hospital_name": order.hospital_name if order else None,
            "test_names": matched,
            "specimen_name": specimen,
            "accession_date": order.accession_date if order else None,
        })

    return result
