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


def infer_micro_culture_types(test_names: list[str], specimen_name: str | None = None) -> list[str]:
    """검사명 목록 + 검체명으로 가능한 배양 타입 목록 반환 (중복 제거)"""
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
# 외주 / 삼광 확장 분류 규칙
# ──────────────────────────────────────────────────────────────────────────────

OUTSOURCE_CODES = {"11", "12", "43", "45"}
OUTSOURCE_CODE_76 = "76"

OUTSOURCE_EXCLUDED_HOSPITALS = {
    "아인병원",
    "금천수병원",
    "삼성장편한내과",
    "브라운소아청소년과의원",
    "황창연내과",
    "원주센텀병원",
    "예손병원",
}

SAMKWANG_HOSPITAL = "연세지안비뇨의학과"

OUTSOURCE_CODE_14 = "14"
YESON_HOSPITAL = "예손병원"


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


def infer_culture_type_extended(
    accession_no: str,
    test_names: list[str],
    specimen_name: str | None,
    hospital_name: str | None,
) -> list[str]:
    """
    기존 infer_micro_culture_types에 외주·삼광 규칙을 추가한 확장 분류 함수.

    우선순위:
      1. 검사명에 Ordinary culture & Sensitivity (disk) 포함 → 삼광
      2. 분류코드 14 + 예손병원 → 외주 (외주 제외 병원 규칙보다 우선)
      3. 분류코드 76:
         a. 연세지안비뇨의학과 + Urine → 삼광
         b. 연세지안비뇨의학과 + Urine 아님 → 기존 매핑 (외주 제외)
         c. 그 외 병원 → 외주
      4. 외주 제외 병원 여부 확인
      5. 분류코드 11·12·43·45 → 외주
      6. 기존 infer_micro_culture_types 매핑
    """
    # 1. Ordinary disk culture → 삼광
    if _has_ordinary_disk(test_names):
        return ["삼광"]

    code = get_classification_code(accession_no)
    hosp = (hospital_name or "").strip()
    sp = normalize_text(specimen_name)

    # 2. 분류코드 14 + 예손병원 → 외주 (외주 제외 병원 규칙보다 우선 적용)
    if code == OUTSOURCE_CODE_14 and hosp == YESON_HOSPITAL:
        return ["외주"]

    # 3. 분류코드 76 전용 규칙
    if code == OUTSOURCE_CODE_76:
        if hosp == SAMKWANG_HOSPITAL:
            if "urine" in sp:
                return ["삼광"]
            return infer_micro_culture_types(test_names, specimen_name)
        return ["외주"]

    # 4·5. 외주 분류코드 체크 (제외 병원은 기존 매핑으로 pass-through)
    if code in OUTSOURCE_CODES and hosp not in OUTSOURCE_EXCLUDED_HOSPITALS:
        return ["외주"]

    # 6. 기존 매핑
    return infer_micro_culture_types(test_names, specimen_name)
