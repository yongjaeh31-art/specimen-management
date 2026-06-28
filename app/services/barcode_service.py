import re

_WHITESPACE_RE = re.compile(r"\s+")
_NON_DIGIT_RE = re.compile(r"\D")
SCANNER_BARCODE_LENGTH = 15
ACCESSION_START = 6
ACCESSION_END = 13


def normalize_accession_input(value: str | None) -> str:
    """바코드 스캐너/수기 입력값을 접수번호로 정규화.

    바코드 스캐너는 '접수일자(6) + 접수번호(7) + suffix(2)' 구조의 15자리 숫자를
    찍어낸다 (예: 260627110117400 → 접수번호 1101174). 수기 입력은 7자리 접수번호
    그대로 들어오므로 변경하지 않는다.
    """
    if value is None:
        return ""
    cleaned = _WHITESPACE_RE.sub("", value.strip())
    digits = _NON_DIGIT_RE.sub("", cleaned)
    if len(digits) == SCANNER_BARCODE_LENGTH:
        return digits[ACCESSION_START:ACCESSION_END]
    return cleaned
