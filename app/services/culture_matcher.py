def normalize_text(value: str | None) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum() or "가" <= ch <= "힣")


def infer_culture_for_test(test_name: str, specimen_name: str | None = None) -> str | None:
    """
    단일 검사명 + 검체명으로 배양 소분류 타입 결정.
    매핑:
      보건증 Salmonella & Shigella culture (아인 포함) → 보건증
      CRE culture & Sensitivity (MIC)                 → CRE culture
      VRE culture & Sensitivity (MIC)                 → VRE culture
      Ordinary culture & Sensitivity (MIC) + Urine    → Urine culture
      Ordinary culture & Sensitivity (MIC) + Sputum   → Sputum culture
      Ordinary culture & Sensitivity (MIC) + Tip      → Tip culture
      Ordinary culture & Sensitivity (MIC) + Rectal/Stool → Stool/Rectal culture
      Ordinary culture & Sensitivity (MIC) + Bronchial washing → Bronchial washing culture
      Ordinary culture & Sensitivity (MIC) 기타        → Other culture
    """
    n = normalize_text(test_name)
    sp = normalize_text(specimen_name)

    # 보건증 (아인 포함)
    if "보건증" in n or ("salmonella" in n and "shigella" in n):
        return "보건증"

    # GBS (산전) — CRE/VRE보다 먼저 체크
    if "gbs" in n and ("culture" in n or "배양" in n or "sensitivity" in n):
        return "산전 GBS 배양검사"

    # Mycoplasma / Ureaplasma — Culture 검사명만 포함 (PCR 등 제외)
    if ("mycoplasma" in n or "ureaplasma" in n) and ("culture" in n or "배양" in n):
        return "Mycoplasma & Ureaplasma Culture"

    # CRE / VRE — 검사명에 명시된 경우 검체명 무관
    if "cre" in n and ("culture" in n or "배양" in n):
        return "CRE culture"
    if "vre" in n and ("culture" in n or "배양" in n):
        return "VRE culture"

    # Ordinary culture & Sensitivity → 검체명으로 세부 분류
    is_ordinary = "ordinaryculture" in n or ("culture" in n and "sensitivity" in n)
    has_culture = "culture" in n or "배양" in n

    if is_ordinary or has_culture:
        if "urine" in sp or "random" in sp or "소변" in sp:
            return "Urine culture"
        if "sputum" in sp or "객담" in sp:
            return "Sputum culture"
        if "rectalswab" in sp or "stool" in sp or "대변" in sp or "직장" in sp:
            return "Stool/Rectal culture"
        if "tip" in sp:
            return "Tip culture"
        if "bronchialwash" in sp or "기관지세척" in sp:
            return "Bronchial washing culture"
        # 검체명으로 분류 불가 + Ordinary → Other
        if is_ordinary:
            return "Other culture"

    return None


def _legacy_infer_micro_culture_types(test_names: list[str], specimen_name: str | None = None) -> list[str]:
    """기존(외주/삼광 도입 이전) 미생물 소분류 매핑 — 절대 변경하지 않는다.
    accession_no 없이 호출되는 모든 기존 호출부의 동작은 이 함수 그대로 유지된다."""
    found: list[str] = []
    seen: set[str] = set()
    for name in test_names:
        ct = infer_culture_for_test(name, specimen_name)
        if ct and ct not in seen:
            found.append(ct)
            seen.add(ct)

    # 직접 매핑이 없으면 검사명 전체를 합쳐 fallback 탐색
    if not found:
        joined = " ".join(normalize_text(n) for n in test_names)
        if "urineculture" in joined or ("소변" in joined and "배양" in joined):
            found.append("Urine culture")
        elif "sputumculture" in joined or ("객담" in joined and "배양" in joined):
            found.append("Sputum culture")
        elif "stoolculture" in joined or "rectalculture" in joined or ("대변" in joined and "배양" in joined):
            found.append("Stool/Rectal culture")
        elif "tipculture" in joined:
            found.append("Tip culture")
        elif "bronchialwashingculture" in joined or "bronchialwashinculture" in joined:
            found.append("Bronchial washing culture")
        elif "culture" in joined or "배양" in joined:
            found.append("Other culture")

    return found


def infer_micro_culture_types(
    test_names: list[str],
    specimen_name: str | None = None,
    accession_no: str | None = None,
    hospital_name: str | None = None,
    workday_type: str = "weekday",
) -> list[str]:
    """검사명 목록 + 검체명으로 가능한 배양 타입 목록 반환.

    하위 호환: accession_no를 넘기지 않는 기존 호출부는 동작이 전혀 바뀌지 않는다
    (기존 infer_micro_culture_types 매핑만 수행).

    accession_no(+ hospital_name)를 넘기면 외주/삼광 확장 규칙(평일/토요일 기준,
    workday_type="weekday"|"saturday")을 우선 적용하고, 해당하지 않으면 기존
    매핑으로 폴스루한다.
    """
    if not accession_no:
        return _legacy_infer_micro_culture_types(test_names, specimen_name)

    # 평일/토요일 공통 최우선 규칙: Ordinary culture & Sensitivity (disk) → 삼광
    if _has_ordinary_disk(test_names):
        return ["삼광"]

    classify = _classify_saturday if workday_type == "saturday" else _classify_weekday
    result = classify(accession_no, test_names, specimen_name, hospital_name)
    if result is not None:
        return result

    return _legacy_infer_micro_culture_types(test_names, specimen_name)


def is_matching_micro_culture(test_names: list[str], specimen_name: str | None, selected_culture_type: str) -> bool:
    inferred = infer_micro_culture_types(test_names, specimen_name)
    if selected_culture_type in inferred:
        return True
    # Other culture는 미분류 배양검사에 허용
    if selected_culture_type == "Other culture":
        return any(
            "culture" in normalize_text(name) or "배양" in normalize_text(name)
            for name in test_names
        )
    return False


# ──────────────────────────────────────────────────────────────────────────────
# 외주 / 삼광 확장 분류 규칙 (평일 / 토요일 기준)
# ──────────────────────────────────────────────────────────────────────────────

WEEKDAY = "weekday"
SATURDAY = "saturday"

# 외주 후보 분류코드: 11·12·43·45·76
OUTSOURCE_CODES = {"11", "12", "43", "45"}
OUTSOURCE_CODE_76 = "76"
OUTSOURCE_CODES_ALL = OUTSOURCE_CODES | {OUTSOURCE_CODE_76}

OUTSOURCE_EXCLUDED_HOSPITALS_RAW = {
    "아인병원",
    "금천수병원",
    "삼성장편한내과",
    "브라운소아청소년과의원",
    "황창연내과",
    "원주센텀병원",
    "예손병원",
}
OUTSOURCE_EXCLUDED_HOSPITALS = {normalize_text(h) for h in OUTSOURCE_EXCLUDED_HOSPITALS_RAW}

SAMKWANG_HOSPITAL = "연세지안비뇨의학과"
_SAMKWANG_HOSPITAL_NORM = normalize_text(SAMKWANG_HOSPITAL)

OUTSOURCE_CODE_14 = "14"
YESON_HOSPITAL = "예손병원"
_YESON_HOSPITAL_VARIANTS = {normalize_text("예손병원"), normalize_text("에손병원")}

SUWON_DUKSAN_CODE = "15"
_SUWON_DUKSAN_HOSPITAL_NORM = normalize_text("수원덕산병원")


def get_classification_code(accession_no: str) -> str:
    """접수번호 앞 2자리 숫자 분류코드 반환. 2자리 미만이거나 숫자가 아니면 빈 문자열."""
    s = (accession_no or "").strip()
    prefix = s[:2]
    return prefix if len(prefix) == 2 and prefix.isdigit() else ""


def _has_ordinary_disk(test_names: list[str]) -> bool:
    """검사명 중 'Ordinary culture & Sensitivity (disk)' 포함 여부 확인."""
    for name in test_names:
        n = normalize_text(name)
        # normalize 후: "ordinaryculture" + "sensitivity" + "disk" 세 키워드 모두 포함 시 매칭
        if "ordinaryculture" in n and "sensitivity" in n and "disk" in n:
            return True
    return False


def _any_test_is(test_names: list[str], specimen_name: str | None, target_type: str) -> bool:
    """검사명 목록 중 하나라도 기존 단일 매핑 결과가 target_type과 일치하는지 확인."""
    return any(infer_culture_for_test(name, specimen_name) == target_type for name in test_names)


def _is_health_cert_test(name: str) -> bool:
    """보건증 Salmonella & Shigella culture (아인 포함 여부 무관)"""
    n = normalize_text(name)
    return "보건증" in n or ("salmonella" in n and "shigella" in n)


def _is_health_cert_ain_variant(name: str) -> bool:
    """보건증 Salmonella & Shigella culture(아인) 전용 변형 여부"""
    n = normalize_text(name)
    return _is_health_cert_test(name) and "아인" in n


def _norm_hospital(hospital_name: str | None) -> str:
    return normalize_text(hospital_name)


def _classify_weekday(
    accession_no: str,
    test_names: list[str],
    specimen_name: str | None,
    hospital_name: str | None,
) -> list[str] | None:
    """평일 기준 외주/삼광 분류. None 반환 시 기존 미생물 매핑 적용."""
    code = get_classification_code(accession_no)
    hosp = _norm_hospital(hospital_name)
    sp = normalize_text(specimen_name)

    # 2·3. 분류코드 76 + 연세지안비뇨의학과
    if code == OUTSOURCE_CODE_76 and hosp == _SAMKWANG_HOSPITAL_NORM:
        return ["삼광"] if "urine" in sp else None

    # 4. GBS / Mycoplasma 예외 → 외주 아님, 기존 매핑
    if (
        _any_test_is(test_names, specimen_name, "산전 GBS 배양검사")
        or _any_test_is(test_names, specimen_name, "Mycoplasma & Ureaplasma Culture")
    ):
        return None

    # 5. 보건증 (아인 포함/미포함 모두) → 외주 아님, 기존 매핑(결과: 보건증)
    if any(_is_health_cert_test(name) for name in test_names):
        return None

    # 6. 분류코드 14 + 예손병원(오타 포함) → 외주 (외주 제외 병원 규칙보다 우선)
    if code == OUTSOURCE_CODE_14 and hosp in _YESON_HOSPITAL_VARIANTS:
        return ["외주"]

    # 7. 외주 제외 병원 → 기존 매핑
    if hosp in OUTSOURCE_EXCLUDED_HOSPITALS:
        return None

    # 8. 분류코드 11·12·43·45·76 → 외주
    if code in OUTSOURCE_CODES_ALL:
        return ["외주"]

    # 9. 그 외 → 기존 매핑
    return None


def _classify_saturday(
    accession_no: str,
    test_names: list[str],
    specimen_name: str | None,
    hospital_name: str | None,
) -> list[str] | None:
    """토요일 기준 외주/삼광 분류. None 반환 시 기존 미생물 매핑 적용."""
    code = get_classification_code(accession_no)
    hosp = _norm_hospital(hospital_name)
    sp = normalize_text(specimen_name)

    # 2·3. 분류코드 76 + 연세지안비뇨의학과
    if code == OUTSOURCE_CODE_76 and hosp == _SAMKWANG_HOSPITAL_NORM:
        return ["삼광"] if "urine" in sp else None

    # 4. GBS / Mycoplasma 예외 → 외주 아님, 기존 매핑
    if (
        _any_test_is(test_names, specimen_name, "산전 GBS 배양검사")
        or _any_test_is(test_names, specimen_name, "Mycoplasma & Ureaplasma Culture")
    ):
        return None

    has_ain_cert = any(_is_health_cert_ain_variant(name) for name in test_names)
    has_plain_cert = any(
        _is_health_cert_test(name) and not _is_health_cert_ain_variant(name)
        for name in test_names
    )

    # 5. 보건증(아인) → 외주 아님, 기존 매핑(결과: 보건증)
    if has_ain_cert:
        return None

    # 6. 외주 제외 병원이라도 CRE/VRE culture 포함 시 → 외주
    if hosp in OUTSOURCE_EXCLUDED_HOSPITALS:
        if (
            _any_test_is(test_names, specimen_name, "CRE culture")
            or _any_test_is(test_names, specimen_name, "VRE culture")
        ):
            return ["외주"]

    # 7. 분류코드 11·12·43·45·76 + 보건증(비-아인) 포함 → 외주
    if code in OUTSOURCE_CODES_ALL and has_plain_cert:
        return ["외주"]

    # 8. 분류코드 15 + 수원덕산병원 → 외주 아님, 기존 매핑
    if code == SUWON_DUKSAN_CODE and hosp == _SUWON_DUKSAN_HOSPITAL_NORM:
        return None

    # 9. 분류코드 14 + 예손병원(오타 포함) → 외주
    if code == OUTSOURCE_CODE_14 and hosp in _YESON_HOSPITAL_VARIANTS:
        return ["외주"]

    # 10. 외주 제외 병원 → 기존 매핑
    if hosp in OUTSOURCE_EXCLUDED_HOSPITALS:
        return None

    # 11. 분류코드 11·12·43·45·76 → 외주
    if code in OUTSOURCE_CODES_ALL:
        return ["외주"]

    # 12. 그 외 → 기존 매핑
    return None


def infer_culture_type_extended(
    accession_no: str,
    test_names: list[str],
    specimen_name: str | None,
    hospital_name: str | None,
    workday_type: str = WEEKDAY,
) -> list[str]:
    """기존 infer_micro_culture_types에 외주·삼광 규칙을 추가한 확장 분류 함수.
    하위 호환 wrapper — infer_micro_culture_types(accession_no=...)로 위임."""
    return infer_micro_culture_types(
        test_names,
        specimen_name,
        accession_no=accession_no,
        hospital_name=hospital_name,
        workday_type=workday_type,
    )


def classify_order_culture_types(
    accession_no: str,
    tests: list[tuple[str, str | None]],
    order_specimen_name: str | None,
    hospital_name: str | None,
    workday_type: str = WEEKDAY,
) -> list[str]:
    """접수번호 단위 확장 분류 — 검사별로 검체명이 다를 수 있는 경우(예: 같은
    접수번호에 일반 소변배양 + CRE 직장도자 검체가 함께 온 경우) 대응.

    tests: (검사명, 검사별_검체명 또는 None) 목록. 검사별 검체명이 None이면
    order_specimen_name(접수 단위 검체명)을 사용한다.

    검체별로 그룹을 나눠 각각 infer_culture_type_extended를 적용하고 결과를
    합친다 — 모든 검사가 같은 검체(또는 전부 None)면 기존과 동일하게 동작한다.
    """
    groups: dict[str | None, list[str]] = {}
    for test_name, per_test_specimen in tests:
        key = per_test_specimen or order_specimen_name
        groups.setdefault(key, []).append(test_name)

    result: list[str] = []
    seen: set[str] = set()
    for specimen, names in groups.items():
        for ct in infer_culture_type_extended(
            accession_no, names, specimen, hospital_name, workday_type=workday_type
        ):
            if ct not in seen:
                seen.add(ct)
                result.append(ct)
    return result
