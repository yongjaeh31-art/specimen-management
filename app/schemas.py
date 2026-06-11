from pydantic import BaseModel


SPECIMEN_CATEGORIES = ["조회만", "Urine", "수송배지", "Other", "Serum", "EDTA", "NaF"]
DEPARTMENT_MAJORS = [
    "미생물",
    "분자진단",
    "세포병리",
    "세포",
    "요경검",
    "A/S형광",
    "임상화학",
    "진단혈액",
    "면역/혈청",
    "외주",
    "기타/확인필요",
]
MICRO_CULTURE_TYPES = [
    "Urine culture",
    "Sputum culture",
    "Stool/Rectal culture",
    "CRE culture",
    "VRE culture",
    "보건증",
    "Tip culture",
    "Bronchial washing culture",
    "Other culture",
]

DEPARTMENT_SUBCATEGORIES = {
    "미생물": MICRO_CULTURE_TYPES,
    "요경검": [
        "Urine routine",
        "Urine sediment",
        "Microscopy(Urine)",
        "Body fluid microscopy",
        "Pregnancy test",
        "Other urine",
    ],
    "분자진단": [
        "MTB PCR",
        "STI PCR",
        "Respiratory PCR",
        "GI virus PCR",
        "C. difficile PCR",
        "Other PCR",
    ],
}


class ScanRequest(BaseModel):
    accession_no: str
    specimen_category: str | None = None
    client_name: str | None = None
    operator_name: str | None = None
    workstation_name: str | None = None


class CultureScanRequest(BaseModel):
    accession_no: str
    culture_type: str
    client_name: str | None = None
    operator_name: str | None = None
    workstation_name: str | None = None


class SubdivisionScanRequest(BaseModel):
    accession_no: str
    department_name: str
    subcategory: str
    client_name: str | None = None
    operator_name: str | None = None
    workstation_name: str | None = None


class AutoCultureScanRequest(BaseModel):
    """미생물 자동 소분류 스캔 — culture_type 선택 없이 자동 판정"""
    accession_no: str
    rack_size: int = 50          # 50 또는 100 (칸 수)
    client_name: str | None = None
    operator_name: str | None = None
    workstation_name: str | None = None


class ScanResponse(BaseModel):
    accession_no: str
    status: str
    message: str
    order_found: bool
    arrived: bool = False
    patient_name: str | None = None
    patient_age: str | None = None
    specimen_name: str | None = None
    tests: list[dict] = []
    department_cards: list[dict] = []
    aliquot_required: bool = False
    transfer_required: bool = False


class RegisterRequest(BaseModel):
    username: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ApproveUserRequest(BaseModel):
    user_id: int
    admin_password: str


class AdminPasswordRequest(BaseModel):
    admin_password: str
