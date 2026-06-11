from collections import Counter

from sqlalchemy.orm import Session

from app.models import CultureRule, DepartmentSubcategoryRule, RoutingRule
from app.schemas import DEPARTMENT_SUBCATEGORIES


DEFAULT_ROUTING_RULES = [
    ("C.difficile toxin A&B", "외주", False, True),
    ("C. difficile toxin A&B", "외주", False, True),
    ("급성설사 원인바이러스 선별검사", "분자진단", True, True),
    ("급성설사 원인세균 선별검사", "분자진단", True, True),
    ("Non-GY Cytospin(Urine)", "세포", False, True),
    ("Non-GY", "세포", False, True),
    ("Cytospin(Urine)", "세포", False, True),
    ("Urine 10종", "요경검", False, False),
    ("Microscopy(Urine)", "요경검", False, False),
    ("편광현미경 검사", "진단혈액", False, False),
    ("Body Fluid analysis", "진단혈액", False, False),
    ("T.Protein", "임상화학", True, False),
    ("T.Protein(RU)", "임상화학", True, False),
    ("Creatinine(RU)", "임상화학", True, False),
    ("Glucose", "임상화학", True, False),
    ("LDH", "임상화학", True, False),
    ("Gram stain", "미생물", False, True),
    ("AFB stain (항산성형광법)", "A/S형광", False, True),
    ("AFB stain", "미생물", False, True),
    ("폐렴원인균 선별검사", "분자진단", True, True),
    ("Fungus culture & Sensitivity (MIC)", "외주", False, True),
    ("Dysmorphic RBC", "요경검", False, False),
    ("AFB culture", "미생물", False, True),
    ("Gardnerella vaginalis PCR", "분자진단", True, True),
    ("Xpert MTB/RIF", "분자진단", True, True),
    ("culture", "미생물", False, True),
    ("배양", "미생물", False, True),
    ("CRE", "미생물", False, True),
    ("VRE", "미생물", False, True),
    ("PCR", "분자진단", True, True),
    ("유전자", "분자진단", True, True),
    ("cytology", "세포병리", False, True),
    ("세포", "세포병리", False, True),
    ("chemistry", "임상화학", True, False),
    ("AST", "임상화학", True, False),
    ("CBC", "진단혈액", False, False),
    ("혈액", "진단혈액", False, False),
    ("PT", "진단혈액", False, False),
    ("HBs", "면역/혈청", True, False),
    ("Ab", "면역/혈청", True, False),
    ("Ag", "면역/혈청", True, False),
    ("면역", "면역/혈청", True, False),
]

DEFAULT_CULTURE_RULES = [
    ("Urine culture", "U"),
    ("Sputum culture", "SP"),
    ("Stool/Rectal culture", "ST"),
    ("CRE culture", "CRE"),
    ("VRE culture", "VRE"),
    ("보건증", "HC"),
    ("Tip culture", "TIP"),
    ("Bronchial washing culture", "BW"),
    ("Other culture", "OC"),
]

SUBCATEGORY_PREFIXES = {
    "Urine routine": "UR",
    "Urine sediment": "US",
    "Microscopy(Urine)": "UM",
    "Body fluid microscopy": "BF",
    "Pregnancy test": "PG",
    "Other urine": "OU",
    "MTB PCR": "MTB",
    "STI PCR": "STI",
    "Respiratory PCR": "RP",
    "GI virus PCR": "GI",
    "C. difficile PCR": "CD",
    "Other PCR": "OP",
}


def seed_rules(db: Session) -> None:
    for keyword, department, aliquot, transfer in DEFAULT_ROUTING_RULES:
        exists = db.query(RoutingRule).filter(RoutingRule.keyword == keyword).first()
        if not exists:
            db.add(
                RoutingRule(
                    keyword=keyword,
                    department_major=department,
                    aliquot_required=aliquot,
                    transfer_required=transfer,
                )
            )

    for culture_type, prefix in DEFAULT_CULTURE_RULES:
        exists = db.query(CultureRule).filter(CultureRule.culture_type == culture_type).first()
        if not exists:
            db.add(CultureRule(culture_type=culture_type, prefix=prefix, next_sequence=1))

    for department, subcategories in DEPARTMENT_SUBCATEGORIES.items():
        if department == "미생물":
            continue
        for subcategory in subcategories:
            exists = (
                db.query(DepartmentSubcategoryRule)
                .filter(
                    DepartmentSubcategoryRule.department_name == department,
                    DepartmentSubcategoryRule.subcategory == subcategory,
                )
                .first()
            )
            if not exists:
                db.add(
                    DepartmentSubcategoryRule(
                        department_name=department,
                        subcategory=subcategory,
                        prefix=SUBCATEGORY_PREFIXES.get(subcategory, department[:2].upper()),
                        next_sequence=1,
                    )
                )


def classify_test(db: Session, test_name: str, provided_department: str | None = None) -> tuple[str, bool, bool]:
    if provided_department:
        return provided_department, False, False

    normalized = (test_name or "").lower()
    rules = db.query(RoutingRule).all()
    # 구체적인(긴) 키워드가 먼저 매칭되도록 키워드 길이 내림차순 정렬
    for rule in sorted(rules, key=lambda r: len(r.keyword), reverse=True):
        if rule.keyword.lower() in normalized:
            return rule.department_major, rule.aliquot_required, rule.transfer_required
    return "기타/확인필요", False, False


def build_department_cards(tests: list[dict]) -> list[dict]:
    counts = Counter(test["department_major"] for test in tests)
    return [{"department_major": name, "count": count} for name, count in counts.most_common()]
