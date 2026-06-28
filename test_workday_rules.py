import sys
sys.path.insert(0, r"C:\Build\Specimen")

from app.services.culture_matcher import infer_micro_culture_types, infer_culture_type_extended

passed = 0
failed = 0

def check(label, actual, expected):
    global passed, failed
    ok = actual == expected
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"{'OK' if ok else 'FAIL'}: {label} -> {actual!r} (expected {expected!r})")


# ──────────────────────────────────────────────────────────────────
# 2. 기존 미생물 매핑 유지 (accession_no 없이 호출 = legacy 경로, 절대 안 바뀜)
# ──────────────────────────────────────────────────────────────────
check("기존-Urine culture", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "Urine (Random)"), ["Urine culture"])
check("기존-CRE culture", infer_micro_culture_types(["CRE culture & Sensitivity (MIC)"], None), ["CRE culture"])
check("기존-VRE culture", infer_micro_culture_types(["VRE culture & Sensitivity (MIC)"], None), ["VRE culture"])
check("기존-Sputum culture", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "Sputum"), ["Sputum culture"])
check("기존-보건증", infer_micro_culture_types(["보건증 Salmonella & Shigella culture"], None), ["보건증"])
check("기존-보건증(아인)", infer_micro_culture_types(["보건증 Salmonella & Shigella culture(아인)"], None), ["보건증"])
check("기존-Tip culture", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "Tip"), ["Tip culture"])
check("기존-Stool/Rectal(RectalSwab)", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "Rectal Swab"), ["Stool/Rectal culture"])
check("기존-Stool/Rectal(Stool)", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "Stool"), ["Stool/Rectal culture"])
check("기존-Bronchial washing", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "Bronchial washing"), ["Bronchial washing culture"])
check("기존-Other culture", infer_micro_culture_types(["Ordinary culture & Sensitivity (MIC)"], "기타검체"), ["Other culture"])
check("기존-GBS", infer_micro_culture_types(["GBS culture & Sensitivity (MIC)"], None), ["산전 GBS 배양검사"])
check("기존-Mycoplasma", infer_micro_culture_types(["Mycoplasma & Ureaplasma Culture"], None), ["Mycoplasma & Ureaplasma Culture"])


# ──────────────────────────────────────────────────────────────────
# 3. 평일 기준 외주/삼광 매핑
# ──────────────────────────────────────────────────────────────────
check(
    "평일: 11+보건증 -> 보건증(외주 아님)",
    infer_culture_type_extended("1101050", ["보건증 Salmonella & Shigella culture"], None, "어떤병원", workday_type="weekday"),
    ["보건증"],
)
check(
    "평일: 11+일반Ordinary+Urine -> 외주",
    infer_culture_type_extended("1101050", ["Ordinary culture & Sensitivity (MIC)"], "Urine (Random)", "어떤병원", workday_type="weekday"),
    ["외주"],
)
check(
    "평일: 12 코드 -> 외주",
    infer_culture_type_extended("1200024", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "어떤병원", workday_type="weekday"),
    ["외주"],
)
check(
    "평일: 43 코드 -> 외주",
    infer_culture_type_extended("4300123", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "어떤병원", workday_type="weekday"),
    ["외주"],
)
check(
    "평일: 45 코드 -> 외주",
    infer_culture_type_extended("4500001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "어떤병원", workday_type="weekday"),
    ["외주"],
)
check(
    "평일: 76 코드(연세지안 아님) -> 외주",
    infer_culture_type_extended("7600001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "다른병원", workday_type="weekday"),
    ["외주"],
)
check(
    "평일: disk 검사 -> 삼광(최우선)",
    infer_culture_type_extended("1101050", ["Ordinary culture & Sensitivity (disk)"], "Urine", "어떤병원", workday_type="weekday"),
    ["삼광"],
)
check(
    "평일: 14+예손병원 -> 외주",
    infer_culture_type_extended("1400001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "예손병원", workday_type="weekday"),
    ["외주"],
)
check(
    "평일: 11+아인병원(제외병원) -> 기존매핑",
    infer_culture_type_extended("1101050", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "아인병원", workday_type="weekday"),
    ["Urine culture"],
)
check(
    "평일: 11+아인병원+CRE -> 기존매핑(외주 아님, 토요일과 차이)",
    infer_culture_type_extended("1101050", ["CRE culture & Sensitivity (MIC)"], None, "아인병원", workday_type="weekday"),
    ["CRE culture"],
)


# ──────────────────────────────────────────────────────────────────
# 4. 토요일 기준 외주/삼광 매핑
# ──────────────────────────────────────────────────────────────────
check(
    "토요일: 11+보건증 -> 외주",
    infer_culture_type_extended("1101050", ["보건증 Salmonella & Shigella culture"], None, "어떤병원", workday_type="saturday"),
    ["외주"],
)
check(
    "토요일: 11+보건증(아인) -> 보건증(외주 아님)",
    infer_culture_type_extended("1101050", ["보건증 Salmonella & Shigella culture(아인)"], None, "어떤병원", workday_type="saturday"),
    ["보건증"],
)
check(
    "토요일: 14+예손병원 -> 외주",
    infer_culture_type_extended("1400001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "예손병원", workday_type="saturday"),
    ["외주"],
)
check(
    "토요일: 15+수원덕산병원 -> 기존매핑(외주 아님)",
    infer_culture_type_extended("1500001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "수원덕산병원", workday_type="saturday"),
    ["Urine culture"],
)
check(
    "토요일: 11 코드(일반 Ordinary) -> 외주",
    infer_culture_type_extended("1101050", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "어떤병원", workday_type="saturday"),
    ["외주"],
)


# ──────────────────────────────────────────────────────────────────
# 5. GBS / Mycoplasma 예외가 외주보다 먼저 적용 (평일/토요일 공통)
# ──────────────────────────────────────────────────────────────────
check(
    "공통(평일): 11+GBS -> 기존매핑(외주 아님)",
    infer_culture_type_extended("1101050", ["GBS culture & Sensitivity (MIC)"], None, "어떤병원", workday_type="weekday"),
    ["산전 GBS 배양검사"],
)
check(
    "공통(토요일): 11+GBS -> 기존매핑(외주 아님)",
    infer_culture_type_extended("1101050", ["GBS culture & Sensitivity (MIC)"], None, "어떤병원", workday_type="saturday"),
    ["산전 GBS 배양검사"],
)
check(
    "공통(평일): 76+Mycoplasma -> 기존매핑(외주 아님)",
    infer_culture_type_extended("7600001", ["Mycoplasma & Ureaplasma Culture"], None, "어떤병원", workday_type="weekday"),
    ["Mycoplasma & Ureaplasma Culture"],
)
check(
    "공통(토요일): 76+Mycoplasma -> 기존매핑(외주 아님)",
    infer_culture_type_extended("7600001", ["Mycoplasma & Ureaplasma Culture"], None, "어떤병원", workday_type="saturday"),
    ["Mycoplasma & Ureaplasma Culture"],
)


# ──────────────────────────────────────────────────────────────────
# 6. 보건증 평일/토요일 차이
# ──────────────────────────────────────────────────────────────────
# (3,4번에서 이미 검증됨 - 평일 11+보건증->보건증, 토요일 11+보건증->외주)
check(
    "토요일: 보건증 코드 아닌 경우(99) -> 기존매핑",
    infer_culture_type_extended("9900001", ["보건증 Salmonella & Shigella culture"], None, "어떤병원", workday_type="saturday"),
    ["보건증"],
)


# ──────────────────────────────────────────────────────────────────
# 7. 76 + 연세지안비뇨의학과 Urine/비Urine 분기 (평일/토요일 공통)
# ──────────────────────────────────────────────────────────────────
check(
    "공통(평일): 76+연세지안비뇨의학과+Urine -> 삼광",
    infer_culture_type_extended("7600001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "연세지안비뇨의학과", workday_type="weekday"),
    ["삼광"],
)
check(
    "공통(토요일): 76+연세지안비뇨의학과+Urine -> 삼광",
    infer_culture_type_extended("7600001", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "연세지안비뇨의학과", workday_type="saturday"),
    ["삼광"],
)
check(
    "공통(평일): 76+연세지안비뇨의학과+Stool -> 기존매핑(외주 아님)",
    infer_culture_type_extended("7600001", ["Ordinary culture & Sensitivity (MIC)"], "Stool", "연세지안비뇨의학과", workday_type="weekday"),
    ["Stool/Rectal culture"],
)
check(
    "공통(토요일): 76+연세지안비뇨의학과+Stool -> 기존매핑(외주 아님)",
    infer_culture_type_extended("7600001", ["Ordinary culture & Sensitivity (MIC)"], "Stool", "연세지안비뇨의학과", workday_type="saturday"),
    ["Stool/Rectal culture"],
)


# ──────────────────────────────────────────────────────────────────
# 8. 토요일 CRE/VRE 분류 (기본 외주, 예외 시 기존매핑)
# ──────────────────────────────────────────────────────────────────
check(
    "토요일: 일반병원+CRE -> 외주 (기본 규칙)",
    infer_culture_type_extended("9999999", ["CRE culture & Sensitivity (MIC)"], None, "일반병원", workday_type="saturday"),
    ["외주"],
)
check(
    "토요일: 일반병원+VRE -> 외주 (기본 규칙)",
    infer_culture_type_extended("9999999", ["VRE culture & Sensitivity (MIC)"], None, "일반병원", workday_type="saturday"),
    ["외주"],
)
check(
    "토요일: 아인병원(외주제외)+CRE -> CRE culture (예외1)",
    infer_culture_type_extended("9999999", ["CRE culture & Sensitivity (MIC)"], None, "아인병원", workday_type="saturday"),
    ["CRE culture"],
)
check(
    "토요일: 금천수병원(외주제외)+VRE -> VRE culture (예외1)",
    infer_culture_type_extended("9999999", ["VRE culture & Sensitivity (MIC)"], None, "금천수병원", workday_type="saturday"),
    ["VRE culture"],
)
check(
    "토요일: 분류코드15+수원덕산병원+CRE -> CRE culture (예외2)",
    infer_culture_type_extended("1500981", ["CRE culture & Sensitivity (MIC)"], None, "수원덕산병원", workday_type="saturday"),
    ["CRE culture"],
)
check(
    "토요일: 분류코드15+수원덕산병원+VRE -> VRE culture (예외2)",
    infer_culture_type_extended("1500981", ["VRE culture & Sensitivity (MIC)"], None, "수원덕산병원", workday_type="saturday"),
    ["VRE culture"],
)
check(
    "평일: 일반병원+CRE -> 기존매핑(외주 아님, 토요일과 차이)",
    infer_culture_type_extended("9999999", ["CRE culture & Sensitivity (MIC)"], None, "일반병원", workday_type="weekday"),
    ["CRE culture"],
)
check(
    "평일: 일반병원+VRE -> 기존매핑(외주 아님, 토요일과 차이)",
    infer_culture_type_extended("9999999", ["VRE culture & Sensitivity (MIC)"], None, "일반병원", workday_type="weekday"),
    ["VRE culture"],
)
check(
    "토요일: 아인병원+Urine(CRE/VRE 아님) -> 기존매핑(외주 아님, 영향 없음)",
    infer_culture_type_extended("1101050", ["Ordinary culture & Sensitivity (MIC)"], "Urine", "아인병원", workday_type="saturday"),
    ["Urine culture"],
)


# ──────────────────────────────────────────────────────────────────
# 10. workday_type 없을 때 기본값 weekday로 동작
# ──────────────────────────────────────────────────────────────────
check(
    "기본값: workday_type 생략 -> weekday와 동일(11+보건증->보건증)",
    infer_culture_type_extended("1101050", ["보건증 Salmonella & Shigella culture"], None, "어떤병원"),
    ["보건증"],
)
check(
    "기본값: infer_micro_culture_types accession_no만 줘도 weekday 기본 적용",
    infer_micro_culture_types(["보건증 Salmonella & Shigella culture"], None, accession_no="1101050", hospital_name="어떤병원"),
    ["보건증"],
)

# 공통: 14 + 예손병원 (평일/토요일 무관하게 외주, 이미 위에서 둘 다 확인)

print(f"\n총 {passed + failed}건 중 통과 {passed}건, 실패 {failed}건")
sys.exit(1 if failed else 0)
