from io import BytesIO
import re

import pandas as pd
from sqlalchemy.orm import Session

from collections import defaultdict

from app.models import DepartmentRoute, ImportBatch, MicroCulturePlan, Order, OrderTest, SpecimenArrival
from app.services.culture_matcher import infer_culture_type_extended, infer_micro_culture_types
from app.services.routing_service import build_department_cards, classify_test


COLUMN_ALIASES = {
    "accession_no": [
        "accession_no",
        "accession",
        "\uc811\uc218\ubc88\ud638",
        "\uc811\uc218 \ubc88\ud638",
        "\uc811\uc218no",
        "\uc811\uc218 no",
        "\uc811\uc218",
        "\ubc14\ucf54\ub4dc",
        "\uac80\uccb4\ubc88\ud638",
        "\uac80\uccb4 \ubc88\ud638",
    ],
    "patient_name": [
        "patient_name",
        "patient",
        "\ud658\uc790\uba85",
        "\uc131\uba85",
        "\uc218\uc9c4\uc790\uba85",
        "\uc218\uc9c4\uc790",
        "\uc218\uac80\uc790\uba85",   # \uc218\uac80\uc790\uba85
        "\uc218\uac80\uc790",          # \uc218\uac80\uc790
    ],
    "patient_age": [
        "patient_age",
        "age",
        "\ub098\uc774",
        "\uc5f0\ub839",
        "\ub9cc\ub098\uc774",
    ],
    "patient_id": [
        "patient_id",
        "\ud658\uc790\ubc88\ud638",
        "\ucc28\ud2b8\ubc88\ud638",
        "\ub4f1\ub85d\ubc88\ud638",
        "\ubcd1\ub85d\ubc88\ud638",
    ],
    "hospital_name": [
        "hospital_name",
        "hospital",
        "\ubcd1\uc6d0\uba85",
        "\ubcd1\uc6d0",
        "\uc758\ub8cc\uae30\uad00",
        "\uc758\ub8cc\uae30\uad00\uba85",
        "\uac70\ub798\ucc98\uba85",   # \uac70\ub798\ucc98\uba85
        "\uac70\ub798\ucc98",          # \uac70\ub798\ucc98
    ],
    "specimen_name": [
        "specimen_name",
        "specimen",
        "\uac80\uccb4\uba85",
        "\uac80\uccb4",
        "\uc7ac\ub8cc\uba85",
    ],
    "test_code": [
        "test_code",
        "\uac80\uc0ac\ucf54\ub4dc",
        "\uac80\uc0ac \ucf54\ub4dc",
        "code",
        "\ucc98\ubc29\ucf54\ub4dc",
    ],
    "test_name": [
        "test_name",
        "\uac80\uc0ac\ud56d\ubaa9",
        "\uac80\uc0ac \ud56d\ubaa9",
        "\uac80\uc0ac\uba85",
        "\uac80\uc0ac",
        "\ucc98\ubc29\uba85",
        "\ud56d\ubaa9\uba85",
    ],
    "department_major": [
        "department_major",
        "\ud559\ubd80",
        "\ubd80\uc11c",
        "\ub300\ubd84\ub958",
        "\uac80\uc0ac\ubd80\uc11c",
    ],
    "aliquot_required": [
        "aliquot_required",
        "\ubd84\uc8fc\ud544\uc694",
        "\ubd84\uc8fc \ud544\uc694",
        "\ubd84\uc8fc",
    ],
    "transfer_required": [
        "transfer_required",
        "\uc804\ub2ec\ud544\uc694",
        "\uc804\ub2ec \ud544\uc694",
        "\uc804\ub2ec",
    ],
    "accession_date": [
        "accession_date",
        "\uc811\uc218\uc77c\uc790",
        "\uc811\uc218\uc77c",
        "\uc811\uc218 \uc77c\uc790",
        "\uc811\uc218\uc77c\uc2dc",
        "\uc218\ud0c1\uc77c\uc790",       # \uc678\uc8fc/\uc218\ud0c1 LIS \uc2dc\uc2a4\ud15c
        "\uc218\ud0c1\uc77c",
        "\uc218\ud0c1\uc77c\uc2dc",
        "\uc758\ub8b0\uc77c\uc790",
        "\uc758\ub8b0\uc77c",
        "\ucc98\ubc29\uc77c\uc790",
        "\ucc98\ubc29\uc77c",
        "\uac80\uc0ac\uc758\ub8b0\uc77c\uc790",
        "\uac80\uc0ac\uc758\ub8b0\uc77c",
        "\uac80\uccb4\uc811\uc218\uc77c\uc790",
        "\uac80\uccb4\uc811\uc218\uc77c",
        "\uac80\uccb4\uc811\uc218\uc77c\uc2dc",
        "date",
    ],
}

# \ud30c\uc77c \uba54\ud0c0\ub370\uc774\ud130 \ud589\uc5d0\uc11c \ub0a0\uc9dc \ucd94\ucd9c\uc5d0 \uc0ac\uc6a9
_FILE_DATE_RE = re.compile(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})")

TEST_KEYWORDS = [
    "culture",
    "stain",
    "sensitivity",
    "mic",
    "pcr",
    "gram",
    "fungus",
    "afb",
    "cbc",
    "ast",
    "alt",
    "glucose",
    "\ubc30\uc591",
    "\uc5fc\uc0c9",
    "\uac80\uc0ac",
    "\ud56d\ubaa9",
    "\uade0",
    "\ud608\uc561",
    "\ud654\ud559",
]

TEST_NAME_REPLACEMENTS: dict[str, str] = {}  # \uac15\uc81c \uc774\ub984 \ubcc0\ud658 \uc5c6\uc74c \u2014 \uc6d0\ubcf8 \uac80\uc0ac\uba85 \uc720\uc9c0


def _truthy(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "y", "yes", "\ud544\uc694", "o", "\uc608"}


def _normalize_key(value) -> str:
    return "".join(
        ch for ch in str(value).strip().lower() if ch.isalnum() or "\uac00" <= ch <= "\ud7a3"
    )


NORMALIZED_ALIASES = {
    key: {_normalize_key(alias) for alias in aliases}
    for key, aliases in COLUMN_ALIASES.items()
}


def _clean_cell(value) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _parse_patient_text(value: str) -> tuple[str | None, str | None]:
    text = _clean_cell(value)
    if not text:
        return None, None
    match = re.match(r"^(?P<name>.+?)\s*\((?P<body>[^)]*)\)\s*$", text)
    if not match:
        return None, None
    name = match.group("name").strip()
    body = match.group("body")
    age_match = re.search(r"(\d{1,3})", body)
    age = age_match.group(1) if age_match else None
    return name or None, age


def _extract_patient_info(row: dict) -> tuple[str | None, str | None]:
    picked_name = _clean_cell(_pick(row, "patient_name") or "")
    picked_age = _clean_cell(_pick(row, "patient_age") or "")
    parsed_name, parsed_age = _parse_patient_text(picked_name)
    if parsed_name or parsed_age:
        return parsed_name or picked_name or None, parsed_age or picked_age or None
    if picked_name or picked_age:
        return picked_name or None, picked_age or None

    for _, value in row.items():
        parsed_name, parsed_age = _parse_patient_text(value)
        if parsed_name or parsed_age:
            return parsed_name, parsed_age
    return None, None


def _normalize_test_name(value: str) -> str:
    cleaned = _clean_cell(value)
    return TEST_NAME_REPLACEMENTS.get(cleaned.lower(), cleaned)


def _normalized_row(row: dict) -> dict:
    return {_normalize_key(k): (k, v) for k, v in row.items()}


def _pick(row: dict, key: str):
    normalized = _normalized_row(row)
    for alias in NORMALIZED_ALIASES[key]:
        if alias in normalized and pd.notna(normalized[alias][1]):
            return normalized[alias][1]
    return None


def _pick_column(row: dict, key: str) -> str | None:
    normalized = _normalized_row(row)
    for alias in NORMALIZED_ALIASES[key]:
        if alias in normalized:
            return normalized[alias][0]
    return None


def _detect_file_date(raw: pd.DataFrame, header_row: int) -> str | None:
    """
    헤더 이전 메타데이터 행에서 날짜 패턴 추출.
    '기간', '접수일자' 같은 타이틀 셀에 날짜가 있는 LIS 파일 대응.
    """
    # 헤더 이전 행 우선 탐색
    for idx in range(header_row):
        for val in raw.iloc[idx].tolist():
            m = _FILE_DATE_RE.search(str(val))
            if m:
                y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
                return f"{y}-{mo}-{d}"
    return None


def _read_upload(filename: str, content: bytes) -> tuple[pd.DataFrame, str | None]:
    """업로드 파일을 파싱해 (DataFrame, 파일레벨_날짜) 반환."""
    suffix = filename.lower().rsplit(".", 1)[-1]
    if suffix == "csv":
        raw = pd.read_csv(BytesIO(content), dtype=str, header=None).fillna("")
    elif suffix == "xlsx":
        raw = pd.read_excel(BytesIO(content), dtype=str, header=None).fillna("")
    elif suffix == "xls":
        raw = pd.read_excel(BytesIO(content), dtype=str, header=None, engine="xlrd").fillna("")
    else:
        raise ValueError("CSV, XLSX, XLS files can be uploaded.")

    header_row = _find_header_row(raw)
    file_date = _detect_file_date(raw, header_row)
    headers = [_clean_cell(value) or f"col_{idx + 1}" for idx, value in enumerate(raw.iloc[header_row].tolist())]
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = headers
    return df.dropna(how="all").fillna(""), file_date


def _find_header_row(raw: pd.DataFrame) -> int:
    accession_aliases = NORMALIZED_ALIASES["accession_no"]
    best_idx = 0
    best_score = -1
    for idx in range(min(len(raw), 30)):
        normalized_values = {_normalize_key(value) for value in raw.iloc[idx].tolist()}
        score = 0
        if normalized_values & accession_aliases:
            score += 10
        for aliases in NORMALIZED_ALIASES.values():
            if normalized_values & aliases:
                score += 1
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx


def _looks_like_test_value(value: str) -> bool:
    normalized = _normalize_key(value)
    if not normalized or normalized.isdigit():
        return False
    lowered = value.lower()
    return any(keyword in lowered or keyword in normalized for keyword in TEST_KEYWORDS)


def _is_test_column(column_name: str) -> bool:
    normalized = _normalize_key(column_name)
    if normalized in NORMALIZED_ALIASES["test_name"]:
        return True
    return any(token in normalized for token in ["test", "\uac80\uc0ac", "\ud56d\ubaa9", "\ucc98\ubc29"])


def _collect_test_names(row: dict) -> list[str]:
    tests: list[str] = []
    primary_test = _clean_cell(_pick(row, "test_name") or "")
    primary_column = _pick_column(row, "test_name")
    specimen_name = _clean_cell(_pick(row, "specimen_name") or "")

    def add_test(value: str) -> None:
        value = _normalize_test_name(value)
        if value and value not in tests and value != specimen_name:
            tests.append(value)

    if primary_test:
        add_test(primary_test)

    items = list(row.items())
    primary_idx = None
    if primary_column:
        for idx, (column_name, _) in enumerate(items):
            if column_name == primary_column:
                primary_idx = idx
                break

    for idx, (column_name, value) in enumerate(items):
        value = _clean_cell(value)
        if not value:
            continue
        if primary_column and column_name == primary_column:
            continue
        if value in {
            _clean_cell(_pick(row, "accession_no") or ""),
            _clean_cell(_pick(row, "patient_name") or ""),
            _clean_cell(_pick(row, "patient_id") or ""),
            specimen_name,
        }:
            continue

        # Worklists often store one accession per row and then several test-name
        # cells to the right of the first test. Capture those trailing test cells.
        if primary_idx is not None and idx > primary_idx and not value.isdigit():
            add_test(value)
            continue

        if _is_test_column(column_name) or _looks_like_test_value(value):
            add_test(value)

    return tests or ["검사항목 미입력"]


def import_orders(db: Session, filename: str, content: bytes, batch_type: str, is_final: bool) -> dict:
    df, file_date = _read_upload(filename, content)
    if df.empty:
        raise ValueError("The upload file has no data.")

    batch = ImportBatch(filename=filename, batch_type=batch_type, is_final=is_final, imported_rows=0)
    db.add(batch)
    db.flush()

    if is_final:
        db.query(Order).update({Order.is_in_final_batch: False})

    grouped: dict[str, list[dict]] = {}
    for raw_row in df.to_dict(orient="records"):
        row = {str(k).strip(): v for k, v in raw_row.items()}
        accession_no = _clean_cell(_pick(row, "accession_no") or "")
        if accession_no:
            grouped.setdefault(accession_no, []).append(row)

    if not grouped:
        db.rollback()
        raise ValueError("No accession numbers were found. Check the worklist header or accession number column.")

    for accession_no, rows in grouped.items():
        first = rows[0]
        order = db.query(Order).filter(Order.accession_no == accession_no).first()
        if not order:
            order = Order(accession_no=accession_no)
            db.add(order)
            db.flush()

        order.patient_name = _clean_cell(_pick(first, "patient_name") or order.patient_name or "") or None
        parsed_patient_name, parsed_patient_age = _extract_patient_info(first)
        order.patient_name = parsed_patient_name or order.patient_name
        order.patient_age = parsed_patient_age or order.patient_age
        order.patient_id = _clean_cell(_pick(first, "patient_id") or order.patient_id or "") or None
        order.hospital_name = _clean_cell(_pick(first, "hospital_name") or order.hospital_name or "") or None
        order.specimen_name = _clean_cell(_pick(first, "specimen_name") or order.specimen_name or "") or None
        raw_date = _pick(first, "accession_date")
        if raw_date:
            date_str = _clean_cell(str(raw_date))
            # "2026-06-16 00:00:00" → "2026-06-16"
            order.accession_date = date_str[:10] if len(date_str) >= 10 else date_str or None
        elif file_date and not order.accession_date:
            # 행 단위 날짜 컬럼 없을 때 파일 레벨 날짜 사용 (헤더/제목 행에서 추출)
            order.accession_date = file_date
        order.source_batch_id = batch.id
        if is_final:
            order.is_in_final_batch = True

        order.tests.clear()
        db.flush()

        for row in rows:
            provided_department = _clean_cell(_pick(row, "department_major") or "") or None
            aliquot_flag = _truthy(_pick(row, "aliquot_required"))
            transfer_flag = _truthy(_pick(row, "transfer_required"))
            test_code = _clean_cell(_pick(row, "test_code") or "") or None

            for test_name in _collect_test_names(row):
                department, aliquot_by_rule, transfer_by_rule = classify_test(db, test_name, provided_department)
                db.add(
                    OrderTest(
                        order_id=order.id,
                        test_code=test_code,
                        test_name=test_name,
                        department_major=department,
                        aliquot_required=aliquot_flag or aliquot_by_rule,
                        transfer_required=transfer_flag or transfer_by_rule,
                    )
                )

        arrivals = db.query(SpecimenArrival).filter(SpecimenArrival.accession_no == accession_no).all()
        for arrival in arrivals:
            arrival.order_id = order.id
            arrival.is_unregistered = False

        db.query(DepartmentRoute).filter(DepartmentRoute.accession_no == accession_no).delete()
        test_dicts = [
            {"department_major": test.department_major}
            for test in db.query(OrderTest).filter(OrderTest.order_id == order.id).all()
        ]
        for card in build_department_cards(test_dicts):
            db.add(
                DepartmentRoute(
                    accession_no=accession_no,
                    department_major=card["department_major"],
                    test_count=card["count"],
                )
            )

    batch.imported_rows = len(grouped)
    db.flush()

    # ── 미생물 소분류 예정 목록 재생성 (이번 배치 기준) ────────────────────
    _rebuild_micro_culture_plans(db, batch.id, list(grouped.keys()))
    # ────────────────────────────────────────────────────────────────────────

    db.commit()
    return {"batch_id": batch.id, "imported_orders": len(grouped), "is_final": is_final}


def _rebuild_micro_culture_plans(db: Session, batch_id: int, accession_nos: list[str]) -> None:
    """
    업로드된 접수번호 기준으로 미생물 소분류 예정 목록(MicroCulturePlan) 재생성.
    - 이미 DONE 상태인 항목은 유지
    - PENDING 상태 기존 항목 삭제 후 재생성
    - 각 culture_type 내에서 접수번호 오름차순으로 LIS순 부여
    """
    if not accession_nos:
        return

    # 이번 배치 접수번호의 기존 PENDING 계획 삭제
    db.query(MicroCulturePlan).filter(
        MicroCulturePlan.accession_no.in_(accession_nos),
        MicroCulturePlan.status == "PENDING",
    ).delete(synchronize_session=False)

    # 접수번호별 order + tests 조회
    orders = {
        o.accession_no: o
        for o in db.query(Order).filter(Order.accession_no.in_(accession_nos)).all()
    }
    order_ids = [o.id for o in orders.values()]
    tests_by_order: dict[int, list[OrderTest]] = defaultdict(list)
    for t in db.query(OrderTest).filter(OrderTest.order_id.in_(order_ids)).all():
        tests_by_order[t.order_id].append(t)

    # culture_type → [accession_no, ...] 수집
    culture_map: dict[str, list[str]] = defaultdict(list)
    for accno in accession_nos:
        order = orders.get(accno)
        if not order:
            continue
        tests = tests_by_order.get(order.id, [])
        test_names = [t.test_name for t in tests]
        if not test_names:
            continue
        culture_types = infer_culture_type_extended(
            accno, test_names, order.specimen_name, order.hospital_name
        )
        for ct in culture_types:
            # 이미 DONE인 경우 제외
            already_done = db.query(MicroCulturePlan).filter(
                MicroCulturePlan.accession_no == accno,
                MicroCulturePlan.culture_type == ct,
                MicroCulturePlan.status == "DONE",
            ).first()
            if not already_done:
                culture_map[ct].append(accno)

    # culture_type별 접수번호 오름차순 정렬 → LIS순 부여
    for ct, accnos in culture_map.items():
        sorted_accnos = sorted(set(accnos))
        for lis_idx, accno in enumerate(sorted_accnos, start=1):
            db.add(MicroCulturePlan(
                batch_id=batch_id,
                accession_no=accno,
                culture_type=ct,
                lis_order=lis_idx,
                status="PENDING",
            ))
