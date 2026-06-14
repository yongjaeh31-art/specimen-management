from datetime import date
from io import BytesIO
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import Break
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MicroCultureAssignment, MicroCulturePlan
from app.schemas import (
    AutoCultureScanRequest, CultureScanRequest,
    DEPARTMENT_SUBCATEGORIES, MICRO_CULTURE_TYPES, SubdivisionScanRequest,
)
from app.services.micro_service import (
    _assignment_dict, _today_start,
    assign_culture_hole,
    auto_assign_culture_hole,
    get_culture_plan_list,
    get_today_micro_assignments,
)
from app.services.subdivision_service import assign_department_subcategory, combined_assignments

router = APIRouter(prefix="/api/micro", tags=["micro"])


@router.post("/culture-scan")
def culture_scan(request: CultureScanRequest, db: Session = Depends(get_db)):
    try:
        return assign_culture_hole(
            db,
            request.accession_no,
            request.culture_type,
            request.client_name,
            request.operator_name,
            request.workstation_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auto-culture-scan")
def auto_culture_scan(request: AutoCultureScanRequest, db: Session = Depends(get_db)):
    """culture_type 선택 없이 자동 판정 → 50칸 랙 위치 배정"""
    try:
        return auto_assign_culture_hole(
            db,
            request.accession_no,
            request.client_name,
            request.operator_name,
            request.workstation_name,
            rack_size=request.rack_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/today-assignments")
def today_assignments(db: Session = Depends(get_db)):
    """오늘 처리된 전체 미생물 소분류 작업 목록"""
    return get_today_micro_assignments(db)


@router.get("/culture-summary")
def culture_summary(db: Session = Depends(get_db)):
    """모든 culture_type의 오늘 진행 현황 요약 (왼쪽 패널 배지용)"""
    from sqlalchemy import func as sqlfunc
    today = _today_start()
    rows = (
        db.query(
            MicroCulturePlan.culture_type,
            MicroCulturePlan.status,
            sqlfunc.count(MicroCulturePlan.id).label("cnt"),
        )
        .filter(MicroCulturePlan.planned_at >= today)
        .group_by(MicroCulturePlan.culture_type, MicroCulturePlan.status)
        .all()
    )
    summary: dict[str, dict] = {ct: {"culture_type": ct, "total": 0, "done": 0, "pending": 0} for ct in MICRO_CULTURE_TYPES}
    for ct, status, cnt in rows:
        if ct in summary:
            summary[ct]["total"] += cnt
            if status == "DONE":
                summary[ct]["done"] += cnt
            else:
                summary[ct]["pending"] += cnt
    return [v for v in summary.values() if v["total"] > 0]


@router.get("/culture-types")
def culture_types():
    return MICRO_CULTURE_TYPES


@router.get("/culture-plans")
def culture_plans(culture_type: str, db: Session = Depends(get_db)):
    """선택한 culture_type의 예정 목록(PENDING) + 완료 목록(DONE) 조회"""
    return get_culture_plan_list(db, culture_type)


@router.get("/culture-assignments")
def culture_assignments(db: Session = Depends(get_db)):
    rows = (
        db.query(MicroCultureAssignment)
        .order_by(MicroCultureAssignment.assigned_at.desc())
        .limit(500)
        .all()
    )
    return [_assignment_dict(row) for row in rows]


@router.get("/subcategories")
def subcategories():
    return DEPARTMENT_SUBCATEGORIES


@router.post("/subcategory-scan")
def subcategory_scan(request: SubdivisionScanRequest, db: Session = Depends(get_db)):
    try:
        return assign_department_subcategory(
            db,
            request.accession_no,
            request.department_name,
            request.subcategory,
            request.client_name,
            request.operator_name,
            request.workstation_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/subcategory-assignments")
def subcategory_assignments(db: Session = Depends(get_db)):
    return combined_assignments(db)


@router.get("/worklist/export")
def export_worklist(db: Session = Depends(get_db)):
    """오늘 스캔 완료 목록 → 미생물 연관검사 워크리스트 (소분류별 시트, 25행/페이지, A4 가로)"""
    assignments = get_today_micro_assignments(db)
    today_str = date.today().strftime("%Y-%m-%d")

    # 소분류별 그룹핑
    groups: dict[str, list] = {}
    for row in assignments:
        groups.setdefault(row["culture_type"], []).append(row)

    wb = Workbook()
    wb.remove(wb.active)

    thin = Side(style="thin", color="BBBBBB")
    cell_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    COL_NAMES = ["순번", "접수번호", "성명 (성별/나이)", "병원명", "검사명", "검체명"]
    COL_WIDTHS = [5, 13, 16, 20, 38, 14]  # 가로 A4 기준
    NCOLS = len(COL_NAMES)
    DATA_PER_PAGE = 25
    HEADER_ROWS = 3  # 타이틀 + 날짜/페이지 + 컬럼헤더

    if not groups:
        ws = wb.create_sheet("미생물 워크리스트")
        ws.cell(1, 1, "오늘 처리된 미생물 소분류 검체가 없습니다.")
    else:
        for ct, rows in groups.items():
            ws = wb.create_sheet(_safe_sheet_name(ct)[:31])

            # A4 가로 인쇄 설정
            ws.page_setup.paperSize = 9
            ws.page_setup.orientation = "landscape"
            ws.page_setup.fitToPage = True
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.page_margins.left = 0.5
            ws.page_margins.right = 0.5
            ws.page_margins.top = 0.7
            ws.page_margins.bottom = 0.7

            for i, w in enumerate(COL_WIDTHS, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

            total_pages = ceil(len(rows) / DATA_PER_PAGE)
            title_fill = PatternFill("solid", fgColor="1E3A5F")
            hdr_fill = PatternFill("solid", fgColor="D9EAF7")

            for pg in range(total_pages):
                page_rows = rows[pg * DATA_PER_PAGE : (pg + 1) * DATA_PER_PAGE]
                base = pg * (HEADER_ROWS + DATA_PER_PAGE) + 1  # 1-indexed

                # 행1: 메인 타이틀
                ws.merge_cells(start_row=base, start_column=1, end_row=base, end_column=NCOLS)
                tc = ws.cell(base, 1, "미생물 연관검사 워크리스트")
                tc.font = Font(name="굴림", size=16, bold=True, color="FFFFFF")
                tc.fill = title_fill
                tc.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[base].height = 26

                # 행2: 소분류명(좌) + 접수일자(중) + 페이지(우)
                info_row = base + 1
                ws.merge_cells(start_row=info_row, start_column=1, end_row=info_row, end_column=2)
                c = ws.cell(info_row, 1, ct)
                c.font = Font(name="굴림", size=9, bold=True)
                c.alignment = Alignment(horizontal="left", vertical="center", indent=1)

                ws.merge_cells(start_row=info_row, start_column=3, end_row=info_row, end_column=4)
                c = ws.cell(info_row, 3, f"접수일자 :   {today_str}  ~  {today_str}")
                c.font = Font(name="굴림", size=9)
                c.alignment = Alignment(horizontal="center", vertical="center")

                ws.merge_cells(start_row=info_row, start_column=5, end_row=info_row, end_column=NCOLS)
                c = ws.cell(info_row, 5, f"페이지 : {pg + 1} of {total_pages}")
                c.font = Font(name="굴림", size=9)
                c.alignment = Alignment(horizontal="right", vertical="center", indent=1)
                ws.row_dimensions[info_row].height = 15

                # 행3: 컬럼 헤더
                hdr_row = base + 2
                for ci, h in enumerate(COL_NAMES, 1):
                    c = ws.cell(hdr_row, ci, h)
                    c.font = Font(name="굴림", size=8, bold=True)
                    c.fill = hdr_fill
                    c.alignment = Alignment(horizontal="center", vertical="center")
                    c.border = cell_border
                ws.row_dimensions[hdr_row].height = 16

                # 데이터 행
                for i, row in enumerate(page_rows):
                    dr = base + HEADER_ROWS + i
                    seq = pg * DATA_PER_PAGE + i + 1
                    alt_fill = PatternFill("solid", fgColor=("FFFFFF" if i % 2 == 0 else "EBF4FB"))
                    vals = [
                        seq,
                        row.get("accession_no", ""),
                        _patient_text(row),
                        row.get("hospital_name") or "",
                        ", ".join(row.get("test_names") or []),
                        row.get("specimen_name") or "",
                    ]
                    for ci, val in enumerate(vals, 1):
                        c = ws.cell(dr, ci, val)
                        c.font = Font(name="굴림", size=8, bold=(ci == 2))
                        c.fill = alt_fill
                        c.border = cell_border
                        c.alignment = Alignment(
                            horizontal="center" if ci <= 2 else "left",
                            vertical="center",
                        )
                    ws.row_dimensions[dr].height = 14

                # 페이지 나누기 (마지막 페이지 제외)
                if pg < total_pages - 1:
                    last_dr = base + HEADER_ROWS + len(page_rows) - 1
                    ws.row_breaks.append(Break(id=last_dr))

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    fname = f"micro_worklist_{date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/subcategory-assignments/export")
def export_subcategory_assignments(
    department_name: str | None = None,
    subcategory: str | None = None,
    page_no: int | None = None,
    db: Session = Depends(get_db),
):
    rows = combined_assignments(db)
    if department_name:
        rows = [row for row in rows if row["department_name"] == department_name]
    if subcategory:
        rows = [row for row in rows if row["subcategory"] == subcategory]
    if page_no:
        rows = [row for row in rows if row["page_no"] == page_no]

    workbook = Workbook()
    workbook.remove(workbook.active)
    # 처리시간 컬럼 제거 — DB에는 유지, 엑셀 출력에서만 제외
    headers = ["번호", "워크리스트순", "접수번호", "성명/나이", "병원명", "검사명", "검체명", "위치번호"]
    num_cols = len(headers)

    if not rows:
        sheet = workbook.create_sheet("소분류")
        _write_title_row(sheet, "소분류 현황", num_cols)
        for col, h in enumerate(headers, 1):
            sheet.cell(row=2, column=col, value=h)
        _format_sheet(sheet, num_cols)
    else:
        group_keys: list[tuple] = []
        for row in rows:
            key = (row["department_name"], row["subcategory"], row["page_no"])
            if key not in group_keys:
                group_keys.append(key)

        for dept, subcat, pg in group_keys:
            page_rows = [
                row for row in rows
                if row["department_name"] == dept
                and row["subcategory"] == subcat
                and row["page_no"] == pg
            ]
            safe_name = _safe_sheet_name(f"{dept}-{subcat}")[:23]
            sheet = workbook.create_sheet(f"{safe_name}-{pg}")

            # 1행: 소분류 제목
            title = f"{dept} / {subcat}  [{pg}번 묶음  {len(page_rows)}/30]"
            _write_title_row(sheet, title, num_cols)

            # 2행: 헤더
            for col, h in enumerate(headers, 1):
                sheet.cell(row=2, column=col, value=h)

            # 3행~: 데이터 (처리시간 제외)
            for r_idx, row in enumerate(page_rows, 3):
                sheet.cell(r_idx, 1, row["page_item_no"])
                sheet.cell(r_idx, 2, row.get("worklist_order") or "")
                sheet.cell(r_idx, 3, row["accession_no"])
                sheet.cell(r_idx, 4, _patient_text(row))
                sheet.cell(r_idx, 5, row.get("hospital_name") or "")
                sheet.cell(r_idx, 6, ", ".join(row.get("test_names") or []))
                sheet.cell(r_idx, 7, row.get("specimen_name") or "")
                sheet.cell(r_idx, 8, row["location_code"])

            _format_sheet(sheet, num_cols)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=subdivision_assignments.xlsx"},
    )


def _write_title_row(sheet, title: str, num_cols: int) -> None:
    """1행에 소분류명 타이틀 작성 (셀 병합 + 스타일)"""
    cell = sheet.cell(row=1, column=1, value=title)
    cell.font = Font(bold=True, size=13, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="1E3A5F")
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    if num_cols > 1:
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    sheet.row_dimensions[1].height = 30


def _format_sheet(sheet, num_cols: int = 8) -> None:
    """2행 헤더 + 3행~ 데이터 스타일링"""
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    for cell in sheet[2]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    # 처리시간 없이 8컬럼: 번호·워크리스트순·접수번호·성명나이·병원명·검사명·검체명·위치번호
    col_widths = [8, 14, 16, 18, 22, 46, 18, 18]
    for idx, width in enumerate(col_widths[:num_cols], 1):
        sheet.column_dimensions[chr(64 + idx)].width = width
    for row in sheet.iter_rows(min_row=3):
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
    sheet.freeze_panes = "A3"  # 1행(타이틀)+2행(헤더) 고정


def _safe_sheet_name(value: str) -> str:
    for char in ["\\", "/", "*", "?", ":", "[", "]"]:
        value = value.replace(char, "-")
    return value or "소분류"


def _patient_text(row: dict) -> str:
    name = row.get("patient_name") or ""
    age = row.get("patient_age") or ""
    if name and age:
        return f"{name} / {age}세"
    return name or age
