# make_docs.py — 검체관리프로그램 문서 PDF 생성
# 실행: python make_docs.py
# 출력: 문서\설치_안내서.pdf, 문서\관리자_안내서.pdf

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, Table, TableStyle, HRFlowable, KeepTogether,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 폰트 등록 ─────────────────────────────────────────────────────────
FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Malgun",   str(FONT_DIR / "malgun.ttf")))
pdfmetrics.registerFont(TTFont("MalgunBd", str(FONT_DIR / "malgunbd.ttf")))

# ── 색상 ──────────────────────────────────────────────────────────────
C_BLUE   = colors.HexColor("#1e40af")
C_LBLUE  = colors.HexColor("#dbeafe")
C_GRAY   = colors.HexColor("#6b7280")
C_LGRAY  = colors.HexColor("#f3f4f6")
C_GREEN  = colors.HexColor("#166534")
C_LGREEN = colors.HexColor("#dcfce7")
C_RED    = colors.HexColor("#991b1b")
C_LRED   = colors.HexColor("#fee2e2")
C_DARK   = colors.HexColor("#111827")
C_LINE   = colors.HexColor("#e5e7eb")
C_AMBER  = colors.HexColor("#92400e")
C_LAMBER = colors.HexColor("#fef3c7")

W, H = A4  # 595.28 x 841.89

# ── 공통 스타일 ──────────────────────────────────────────────────────
def make_styles():
    base = dict(fontName="Malgun", leading=18)
    return {
        "title"  : ParagraphStyle("title",   fontName="MalgunBd", fontSize=26,
                                   textColor=C_BLUE,  spaceAfter=6),
        "sub"    : ParagraphStyle("sub",     fontName="Malgun",   fontSize=13,
                                   textColor=C_GRAY,  spaceAfter=12),
        "h1"     : ParagraphStyle("h1",      fontName="MalgunBd", fontSize=15,
                                   textColor=C_BLUE,  spaceBefore=14, spaceAfter=6),
        "h2"     : ParagraphStyle("h2",      fontName="MalgunBd", fontSize=12,
                                   textColor=C_DARK,  spaceBefore=10, spaceAfter=4),
        "body"   : ParagraphStyle("body",    **base, fontSize=10, textColor=C_DARK,
                                   spaceAfter=4),
        "bullet" : ParagraphStyle("bullet",  **base, fontSize=10, textColor=C_DARK,
                                   leftIndent=14, spaceAfter=3, bulletIndent=4),
        "note"   : ParagraphStyle("note",    **base, fontSize=9,  textColor=C_AMBER),
        "code"   : ParagraphStyle("code",    fontName="Malgun",   fontSize=9,
                                   textColor=colors.HexColor("#1e3a5f"),
                                   leftIndent=10, spaceAfter=3),
        "small"  : ParagraphStyle("small",   **base, fontSize=8,  textColor=C_GRAY),
        "step_n" : ParagraphStyle("step_n",  fontName="MalgunBd", fontSize=11,
                                   textColor=C_BLUE,  spaceAfter=2, spaceBefore=8),
    }

S = make_styles()

def hr(): return HRFlowable(width="100%", thickness=0.5, color=C_LINE, spaceAfter=8)
def sp(h=6): return Spacer(1, h)

def cover_table(title, subtitle, date="2026-06-20"):
    data = [
        [Paragraph(title,    ParagraphStyle("ct", fontName="MalgunBd", fontSize=22,
                                            textColor=colors.white, leading=28))],
        [Paragraph(subtitle, ParagraphStyle("cs", fontName="Malgun",   fontSize=11,
                                            textColor=colors.HexColor("#bfdbfe"), leading=16))],
        [Paragraph(f"발행일 : {date}",
                   ParagraphStyle("cd", fontName="Malgun", fontSize=9,
                                  textColor=colors.HexColor("#93c5fd")))],
    ]
    t = Table(data, colWidths=[150*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_BLUE),
        ("TOPPADDING",    (0,0), (-1,0), 18),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING",    (0,1), (-1,1), 2),
        ("BOTTOMPADDING", (0,1), (-1,1), 2),
        ("TOPPADDING",    (0,2), (-1,2), 6),
        ("BOTTOMPADDING", (0,2), (-1,2), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_BLUE]),
    ]))
    return t

def info_box(text, bg=C_LBLUE, fg=C_BLUE):
    data = [[Paragraph(text, ParagraphStyle("ib", fontName="Malgun", fontSize=9.5,
                                            textColor=fg, leading=15))]]
    t = Table(data, colWidths=[150*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [4,4,4,4]),
    ]))
    return t

def step_box(num, title, lines):
    hdr = Table(
        [[Paragraph(f"STEP {num}", ParagraphStyle("sn", fontName="MalgunBd", fontSize=9,
                                                  textColor=colors.white)),
          Paragraph(title, ParagraphStyle("st", fontName="MalgunBd", fontSize=11,
                                          textColor=colors.white))]],
        colWidths=[18*mm, 132*mm],
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_BLUE),
        ("LEFTPADDING",   (0,0), (0,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    body_rows = [[Paragraph(l, S["body"])] for l in lines]
    body = Table(body_rows, colWidths=[150*mm])
    body.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_LGRAY),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    wrapper = Table([[hdr], [body]], colWidths=[150*mm])
    wrapper.setStyle(TableStyle([
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("SPACER",        (0,0), (-1,-1), [0,0,0,6]),
    ]))
    return KeepTogether([wrapper, sp(8)])

def file_row(name, color, desc, detail=""):
    d = [
        [Paragraph(f"<b>{name}</b>", ParagraphStyle("fr", fontName="MalgunBd",
                                                     fontSize=10, textColor=color)),
         Paragraph(desc, ParagraphStyle("fd", fontName="Malgun", fontSize=10,
                                         textColor=C_DARK, leading=14))],
    ]
    if detail:
        d.append(["", Paragraph(detail, ParagraphStyle("fdd", fontName="Malgun",
                                                        fontSize=8.5, textColor=C_GRAY,
                                                        leading=13))])
    t = Table(d, colWidths=[48*mm, 102*mm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_LINE),
        ("BACKGROUND",    (0,0), (-1,-1), colors.white),
    ]))
    return t


def build_doc(path, content_fn):
    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Malgun", 8)
        canvas.setFillColor(C_GRAY)
        canvas.drawString(20*mm, 10*mm, "검체관리프로그램")
        canvas.drawRightString(W - 20*mm, 10*mm, f"{doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(
        path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=18*mm, bottomMargin=18*mm,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="normal")
    tmpl = PageTemplate(id="main", frames=[frame], onPage=header_footer)
    doc.addPageTemplates([tmpl])
    story = content_fn()
    doc.build(story)


# ═══════════════════════════════════════════════════════════════════════
#  PDF 1: 사용자 설치 안내서
# ═══════════════════════════════════════════════════════════════════════
def user_guide():
    story = []

    # 표지
    story.append(sp(30))
    story.append(cover_table(
        "검체관리프로그램",
        "초보 사용자를 위한 설치 및 사용 안내서",
    ))
    story.append(sp(12))
    story.append(info_box(
        "이 문서는 파이썬(Python)을 설치하지 않아도 프로그램을 사용할 수 있도록\n"
        "단계별로 안내합니다. 처음 설치하는 분도 아래 순서를 따라하시면 됩니다.",
        bg=C_LBLUE, fg=C_BLUE,
    ))
    story.append(PageBreak())

    # 1. 설치 전 확인
    story.append(Paragraph("1.  설치 전 확인 사항", S["h1"]))
    story.append(hr())

    req = [
        ["항목", "요구 사항", "확인 방법"],
        ["운영체제", "Windows 10 또는 Windows 11", "시작 → 설정 → 시스템 → 정보"],
        ["여유 공간", "200 MB 이상", "파일 탐색기 → C드라이브 우클릭 → 속성"],
        ["네트워크", "같은 건물 내 공유 시 Wi-Fi 또는 유선 LAN", "—"],
        ["파이썬", "불필요 (프로그램 내 포함)", "별도 설치 없음"],
    ]
    t = Table(req, colWidths=[32*mm, 68*mm, 50*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(sp(10))

    # 2. 파일 전달 받기
    story.append(Paragraph("2.  설치 파일 받기", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "관리자로부터 아래 ZIP 파일을 전달받아 PC에 저장합니다.", S["body"]))
    story.append(sp(4))

    fbox = Table(
        [[Paragraph("📦  검체관리프로그램_설치_YYYYMMDD.zip",
                    ParagraphStyle("fn", fontName="MalgunBd", fontSize=11,
                                   textColor=C_BLUE))]],
        colWidths=[150*mm])
    fbox.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_LBLUE),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(fbox)
    story.append(sp(6))
    story.append(info_box(
        "💡  USB 메모리, 네트워크 공유 폴더, 이메일 첨부 등 어떤 방법으로 전달받아도 됩니다.\n"
        "     파일명 중간의 날짜(YYYYMMDD)는 버전에 따라 다를 수 있습니다.",
        bg=C_LGREEN, fg=C_GREEN,
    ))
    story.append(sp(10))

    # 3. 압축 해제
    story.append(Paragraph("3.  ZIP 파일 압축 해제", S["h1"]))
    story.append(hr())
    story.append(step_box(1, "ZIP 파일을 원하는 위치로 이동", [
        "바탕화면 또는 D:\\(데이터 드라이브)에 두는 것을 권장합니다.",
        "경로에 한글이 포함되어도 됩니다.",
        "⚠  Program Files 폴더 안에는 넣지 마세요 (권한 문제).",
    ]))
    story.append(step_box(2, "ZIP 파일을 우클릭 → '모두 압축 풀기' 선택", [
        "Windows 탐색기에서 ZIP 파일을 우클릭합니다.",
        "'모두 압축 풀기(T)...' 를 클릭합니다.",
        "압축을 풀 폴더를 선택하고 '압축 풀기' 버튼을 클릭합니다.",
        "완료 후 '검체관리프로그램' 폴더가 생성됩니다.",
    ]))
    story.append(step_box(3, "폴더 구조 확인", [
        "압축 해제 후 아래와 같은 파일/폴더가 보여야 정상입니다.",
    ]))
    struct = Table([
        [Paragraph("검체관리프로그램 폴더 내 구성", ParagraphStyle("sh", fontName="MalgunBd",
                                                              fontSize=9, textColor=C_BLUE))],
        [Paragraph(
            "  📁  app\n"
            "  📁  python\n"
            "  ▶   검체관리프로그램.exe\n"
            "  📄  시작.bat\n"
            "  📄  네트워크공유.bat",
            ParagraphStyle("sc", fontName="Malgun", fontSize=10, textColor=C_DARK,
                           leading=18, leftIndent=8)
        )],
    ], colWidths=[150*mm])
    struct.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_LBLUE),
        ("BACKGROUND",    (0,1), (-1,1), C_LGRAY),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LINEBELOW",     (0,0), (-1,0), 0.5, C_LINE),
    ]))
    story.append(struct)
    story.append(sp(10))

    # 4. 프로그램 실행
    story.append(Paragraph("4.  프로그램 실행 방법", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "아래 두 가지 방법 중 하나를 선택하면 됩니다. "
        "두 방법 모두 서버를 시작하고 브라우저를 자동으로 엽니다.", S["body"]))
    story.append(sp(6))

    methods = [
        ["방법", "파일", "특징"],
        ["방법 1\n(권장)", "시작.bat\n더블클릭", "콘솔 창이 표시됩니다.\n콘솔 창을 닫으면 서버도 종료됩니다."],
        ["방법 2", "검체관리프로그램.exe\n더블클릭", "콘솔 창 없이 조용히 실행됩니다.\n종료하려면 작업 관리자에서 프로세스 종료."],
    ]
    mt = Table(methods, colWidths=[22*mm, 40*mm, 88*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_LGRAY, colors.white]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(mt)
    story.append(sp(8))
    story.append(info_box(
        "✅  처음 실행 시 4~10초 후 브라우저(Chrome, Edge 등)가 자동으로 열립니다.\n"
        "     브라우저가 열리면 주소창에  http://localhost:8000  이 표시됩니다.",
        bg=C_LGREEN, fg=C_GREEN,
    ))
    story.append(sp(8))
    story.append(info_box(
        "🔒  Windows 보안 경고가 나타나면 '추가 정보' → '실행' 을 클릭하세요.\n"
        "     백신 프로그램이 차단할 경우 예외 처리 후 실행하세요.",
        bg=C_LAMBER, fg=C_AMBER,
    ))
    story.append(sp(10))

    # 5. 매일 사용 방법
    story.append(Paragraph("5.  매일 사용 방법", S["h1"]))
    story.append(hr())

    daily = [
        ["구분", "방법"],
        ["프로그램 시작", "시작.bat 또는 검체관리프로그램.exe 더블클릭\n→ 브라우저 자동 오픈"],
        ["브라우저 닫은 후\n다시 열기",
         "시작.bat을 다시 더블클릭하면 이미 실행 중임을 감지하고\n브라우저만 다시 엽니다 (서버 중복 실행 없음)"],
        ["프로그램 종료", "시작.bat을 실행한 콘솔 창을 닫으면 서버도 함께 종료됩니다."],
        ["데이터 유지 여부",
         "프로그램을 종료했다가 다시 시작해도 모든 데이터는 유지됩니다.\n"
         "새 LIS 파일을 업로드해도 이전 소분류 기록은 삭제되지 않습니다."],
    ]
    dt = Table(daily, colWidths=[38*mm, 112*mm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(dt)
    story.append(sp(10))

    # 6. 네트워크 공유
    story.append(Paragraph("6.  다른 PC에서 접속하기 (네트워크 공유)", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "여러 검사실 PC에서 동시에 사용하려면 서버 PC에서 네트워크공유.bat을 실행합니다.",
        S["body"]))
    story.append(sp(6))
    story.append(step_box(1, "서버 PC에서 네트워크공유.bat 더블클릭", [
        "콘솔 창에 접속 주소(예: http://192.168.1.100:8000)가 표시됩니다.",
        "방화벽 8000 포트를 자동으로 허용합니다 (관리자 권한 필요 시 허용 클릭).",
    ]))
    story.append(step_box(2, "다른 PC의 브라우저에서 접속", [
        "Chrome 또는 Edge를 열고 콘솔 창에 표시된 주소를 입력합니다.",
        "예:  http://192.168.1.100:8000",
        "서버 PC와 같은 Wi-Fi 또는 유선 LAN에 연결되어 있어야 합니다.",
    ]))
    story.append(sp(10))

    # 7. 자주 묻는 질문
    story.append(Paragraph("7.  자주 묻는 질문 (FAQ)", S["h1"]))
    story.append(hr())

    faqs = [
        ("Q.  브라우저가 자동으로 열리지 않습니다.",
         "브라우저(Chrome 또는 Edge)를 직접 열고 주소창에\n"
         "http://localhost:8000  을 입력하세요."),
        ("Q.  '포트 8000이 이미 사용 중' 오류가 납니다.",
         "시작.bat을 다시 더블클릭하면 자동으로 브라우저만 엽니다.\n"
         "또는 작업 관리자(Ctrl+Shift+Esc) → 세부 정보 탭 → python.exe 종료 후 재시도."),
        ("Q.  Windows가 '알 수 없는 앱' 경고를 표시합니다.",
         "'추가 정보'를 클릭한 후 '실행' 버튼을 클릭하세요.\n"
         "이 프로그램은 인터넷 연결 없이 내 PC 안에서만 동작합니다."),
        ("Q.  백신 프로그램이 차단합니다.",
         "백신의 예외 목록에 '검체관리프로그램' 폴더 전체를 추가하세요.\n"
         "관리자(IT 담당자)에게 문의하세요."),
        ("Q.  프로그램을 삭제하려면?",
         "'검체관리프로그램' 폴더 전체를 삭제하면 됩니다.\n"
         "별도의 레지스트리 항목이나 시스템 파일은 생성되지 않습니다."),
    ]
    for q, a in faqs:
        qbox = Table(
            [[Paragraph(q, ParagraphStyle("q", fontName="MalgunBd", fontSize=9.5,
                                          textColor=C_BLUE))],
             [Paragraph(a, ParagraphStyle("a", fontName="Malgun", fontSize=9.5,
                                          textColor=C_DARK, leading=15,
                                          leftIndent=8))]],
            colWidths=[150*mm],
        )
        qbox.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), C_LBLUE),
            ("BACKGROUND",    (0,1), (-1,1), colors.white),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LINEBELOW",     (0,-1), (-1,-1), 0.3, C_LINE),
        ]))
        story.append(qbox)
        story.append(sp(4))

    return story


# ═══════════════════════════════════════════════════════════════════════
#  PDF 2: 관리자 안내서
# ═══════════════════════════════════════════════════════════════════════
def admin_guide():
    story = []

    story.append(sp(30))
    story.append(cover_table(
        "검체관리프로그램",
        "관리자용 파일 기능 및 운영 안내서",
    ))
    story.append(sp(12))
    story.append(info_box(
        "이 문서는 프로그램의 파일 구조, 데이터 관리, 업데이트 방법을 설명합니다.\n"
        "IT 담당자 또는 프로그램 관리자를 위한 자료입니다.",
        bg=C_LBLUE, fg=C_BLUE,
    ))
    story.append(PageBreak())

    # 1. 전체 폴더 구조
    story.append(Paragraph("1.  설치 폴더 구조", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "ZIP 압축 해제 후 '검체관리프로그램' 폴더 내부 구성입니다.", S["body"]))
    story.append(sp(6))

    tree_data = [
        ["경로", "종류", "역할"],
        ["시작.bat",                "런처", "더블클릭으로 서버 시작 + 브라우저 오픈"],
        ["네트워크공유.bat",          "런처", "네트워크 공유 모드 (방화벽 자동 설정)"],
        ["검체관리프로그램.exe",       "런처", "콘솔 없는 GUI 런처 (PyInstaller 컴파일)"],
        ["specimen_routing.db",    "데이터", "SQLite 데이터베이스 — 모든 데이터 저장"],
        ["python\\",               "런타임", "번들 Python 3.11 + 모든 패키지 포함"],
        ["app\\",                  "앱코드", "FastAPI 웹 애플리케이션 소스"],
        ["app\\main.py",           "앱코드", "서버 진입점, DB 초기화·마이그레이션"],
        ["app\\models.py",         "앱코드", "데이터베이스 테이블 스키마 정의"],
        ["app\\database.py",       "앱코드", "DB 연결 설정 (SQLite/PostgreSQL 전환 가능)"],
        ["app\\schemas.py",        "앱코드", "소분류·검사 유형 목록 정의"],
        ["app\\routers\\",         "앱코드", "API 엔드포인트 (micro, scans, imports 등)"],
        ["app\\services\\",        "앱코드", "비즈니스 로직 (소분류 배정, 라우팅 등)"],
        ["app\\templates\\",       "앱코드", "HTML 페이지 템플릿 (Jinja2)"],
        ["app\\static\\",          "앱코드", "CSS / JavaScript 정적 파일"],
    ]
    tw = Table(tree_data, colWidths=[52*mm, 20*mm, 78*mm])
    tw.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tw)
    story.append(sp(10))

    # 2. 데이터베이스 (핵심)
    story.append(Paragraph("2.  데이터베이스 (specimen_routing.db)", S["h1"]))
    story.append(hr())
    story.append(info_box(
        "⚠  이 파일 하나에 모든 업무 데이터가 저장됩니다.\n"
        "   정기적으로 복사본(백업)을 만들어 두세요.",
        bg=C_LRED, fg=C_RED,
    ))
    story.append(sp(6))

    db_tables = [
        ["테이블", "저장 내용"],
        ["orders",                       "LIS 파일에서 업로드한 접수 목록"],
        ["order_tests",                  "각 접수의 검사 항목 목록"],
        ["specimen_arrivals",            "도착 관리 스캔 기록"],
        ["micro_culture_plans",          "미생물 배양 계획 (배치·칸 번호)"],
        ["micro_culture_assignments",    "미생물 소분류 스캔 결과"],
        ["department_subcategory_rules", "소분류별 위치 번호 발급 규칙·순번"],
        ["department_subcategory_assignments", "비미생물 소분류 스캔 결과"],
        ["scan_logs",                    "모든 스캔 이력 로그"],
        ["import_batches",               "LIS 파일 업로드 이력"],
        ["routing_rules",                "검체 라우팅 규칙"],
    ]
    dbt = Table(db_tables, colWidths=[68*mm, 82*mm])
    dbt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(dbt)
    story.append(sp(8))

    story.append(Paragraph("데이터 백업 방법", S["h2"]))
    story.append(Paragraph(
        "서버 종료 상태에서 specimen_routing.db 파일을 복사해 별도 폴더에 보관합니다. "
        "날짜를 파일명에 포함하면 버전 관리가 용이합니다.", S["body"]))
    story.append(Paragraph(
        "예)  specimen_routing_20260620.db", S["code"]))
    story.append(sp(6))

    story.append(Paragraph("데이터 완전 삭제 방법", S["h2"]))
    story.append(info_box(
        "주의: 아래 방법은 복구할 수 없습니다.\n\n"
        "  1.  서버(시작.bat 창)를 먼저 종료합니다.\n"
        "  2.  specimen_routing.db  파일을 삭제합니다.\n"
        "       (같은 폴더의 .db-shm, .db-wal 파일도 함께 삭제)\n"
        "  3.  프로그램을 다시 시작하면 빈 DB가 자동으로 생성됩니다.",
        bg=C_LRED, fg=C_RED,
    ))
    story.append(sp(10))

    # 3. 소분류 리셋 기능
    story.append(Paragraph("3.  소분류 리셋 (출근 기준 초기화)", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "야간 근무(19:00 ~ 다음날 09:00) 종료 후 새 근무를 시작할 때 "
        "소분류 스캔 기록을 초기화하는 기능입니다.", S["body"]))
    story.append(sp(6))

    reset_data = [
        ["항목", "내용"],
        ["버튼 위치", "소분류 탭 (/micro 페이지) 우상단 '리셋' 버튼 (빨간색)"],
        ["기준 시각",
         "KST 19:00 기준 — 현재 시각이 19:00 이후면 '오늘 19:00'\n"
         "현재 시각이 19:00 이전이면 '전날 19:00'"],
        ["삭제 대상",
         "기준 시각 이후 생성된 micro_culture_assignments 레코드\n"
         "기준 시각 이후 생성된 department_subcategory_assignments 레코드\n"
         "삭제된 micro_culture_assignments에 연결된 MicroCulturePlan → PENDING 복원"],
        ["유지 데이터",
         "orders (접수 목록), order_tests (검사 항목)\n"
         "specimen_arrivals (도착 기록), scan_logs (로그)\n"
         "department_subcategory_rules 순번 (리셋 안 됨 → 별도 관리 필요)"],
        ["API 경로", "POST /api/micro/reset-shift"],
    ]
    rt = Table(reset_data, colWidths=[40*mm, 110*mm])
    rt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(rt)
    story.append(sp(10))

    # 4. 업데이트 방법
    story.append(Paragraph("4.  프로그램 업데이트 방법", S["h1"]))
    story.append(hr())

    story.append(Paragraph("4-1.  앱 코드만 업데이트 (권장)", S["h2"]))
    story.append(Paragraph(
        "관리자로부터  검체관리프로그램_업데이트_YYYYMMDD.zip  파일을 받아 진행합니다.",
        S["body"]))
    story.append(sp(4))
    story.append(step_box(1, "서버를 먼저 종료합니다", [
        "시작.bat을 실행한 콘솔 창을 닫습니다.",
    ]))
    story.append(step_box(2, "업데이트 ZIP을 압축 해제합니다", [
        "ZIP 내부의 app 폴더를 확인합니다.",
    ]))
    story.append(step_box(3, "기존 설치 폴더의 app 폴더를 교체합니다", [
        "기존 '검체관리프로그램\\app\\' 폴더 전체를 삭제합니다.",
        "업데이트 ZIP에서 꺼낸 'app' 폴더를 같은 위치에 붙여넣습니다.",
        "데이터베이스(specimen_routing.db)는 변경하지 않습니다.",
    ]))
    story.append(step_box(4, "서버를 다시 시작합니다", [
        "시작.bat을 더블클릭합니다.",
        "DB 스키마가 변경된 경우 자동으로 마이그레이션이 실행됩니다.",
    ]))

    story.append(sp(4))
    story.append(Paragraph("4-2.  전체 재설치 (Python 버전 등 환경 변경 시)", S["h2"]))
    story.append(Paragraph(
        "검체관리프로그램_설치_YYYYMMDD.zip 을 받아 새 폴더에 압축 해제합니다. "
        "기존 specimen_routing.db 파일을 새 설치 폴더로 복사하면 데이터가 유지됩니다.",
        S["body"]))
    story.append(sp(10))

    # 5. 배포 파일 빌드 (개발자용)
    story.append(Paragraph("5.  배포 파일 빌드 방법 (개발자 전용)", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "소스 폴더(C:\\Build\\Specimen)에서 배포 ZIP을 생성하는 방법입니다.", S["body"]))
    story.append(sp(6))

    build_rows = [
        ["파일", "역할"],
        ["빌드_배포파일.bat", "더블클릭으로 ZIP 2종 생성 (빌드_배포파일.ps1 호출)"],
        ["빌드_배포파일.ps1",
         "실제 빌드 로직:\n"
         "① app\\ + python\\ + 런처 파일 → 설치 ZIP\n"
         "② app\\ 폴더만 → 업데이트 ZIP"],
        ["배포\\ 폴더",
         "빌드 결과물 저장 위치\n"
         "검체관리프로그램_설치_YYYYMMDD.zip  (전체, ~55 MB)\n"
         "검체관리프로그램_업데이트_YYYYMMDD.zip  (앱 코드, ~0.1 MB)"],
    ]
    bt = Table(build_rows, colWidths=[52*mm, 98*mm])
    bt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(bt)
    story.append(sp(10))

    # 6. API 주요 엔드포인트
    story.append(Paragraph("6.  주요 API 엔드포인트", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "브라우저 개발자 도구(F12) 또는 http://localhost:8000/docs 에서 확인 가능합니다.",
        S["body"]))
    story.append(sp(6))

    apis = [
        ["메서드", "경로", "기능"],
        ["POST", "/api/imports/upload",                "LIS 엑셀 파일 업로드"],
        ["GET",  "/api/scans/scan/{accession_no}",     "검체 도착 스캔"],
        ["POST", "/api/micro/assign",                  "미생물 소분류 배정"],
        ["POST", "/api/micro/auto-assign",             "미생물 자동 배정"],
        ["GET",  "/api/micro/today-assignments",       "오늘 미생물 배정 목록"],
        ["GET",  "/api/micro/worklist/export",         "워크리스트 Excel 다운로드"],
        ["GET",  "/api/micro/subcategory-assignments", "소분류 현황 전체 조회"],
        ["GET",  "/api/micro/subcategory-assignments/export", "소분류 Excel 다운로드"],
        ["POST", "/api/micro/reset-shift",             "출근 기준 소분류 초기화"],
        ["POST", "/api/micro/assign-dept",             "비미생물 소분류 배정"],
    ]
    at = Table(apis, colWidths=[18*mm, 72*mm, 60*mm])
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR",     (0,1), (0,-1), colors.HexColor("#166534")),
        ("FONTNAME",      (0,1), (0,-1), "MalgunBd"),
    ]))
    story.append(at)

    return story


# ═══════════════════════════════════════════════════════════════════════
#  PDF 3: GitHub 관리자 안내서 (배포 담당자용)
# ═══════════════════════════════════════════════════════════════════════
def github_admin_guide():
    story = []

    story.append(sp(30))
    story.append(cover_table(
        "검체관리프로그램",
        "GitHub 저장소 관리 및 배포 안내서 (관리자용)",
    ))
    story.append(sp(12))
    story.append(info_box(
        "이 문서는 프로그램 코드를 GitHub에 저장하고\n"
        "새 버전을 사용자에게 배포하는 방법을 단계별로 설명합니다.\n"
        "개발·배포 담당자를 위한 자료입니다.",
        bg=C_LBLUE, fg=C_BLUE,
    ))
    story.append(PageBreak())

    # 1. 개요
    story.append(Paragraph("1.  GitHub 배포 구조 개요", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "소스 코드는 GitHub에 저장하고, 사용자가 내려받을 배포 ZIP은 "
        "GitHub Releases에 자동으로 올라갑니다.", S["body"]))
    story.append(sp(8))

    flow = [
        ["단계", "행위자", "내용"],
        ["①  코드 수정", "개발자", "app\\ 폴더의 Python/HTML 파일 수정"],
        ["②  커밋 · 푸시", "개발자", "git commit + git push origin main"],
        ["③  버전 태그", "개발자", "git tag v1.2.0 + git push origin v1.2.0"],
        ["④  자동 빌드", "GitHub Actions", "Python 런타임 다운로드 + 패키지 설치\n+ PDF 생성 + ZIP 압축"],
        ["⑤  릴리즈 게시", "GitHub Actions", "Releases 페이지에 ZIP 2종 자동 업로드"],
        ["⑥  사용자 설치", "사용자", "Releases 페이지에서 ZIP 다운로드 → 압축 해제 → 실행"],
    ]
    ft = Table(flow, colWidths=[28*mm, 30*mm, 92*mm])
    ft.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(ft)
    story.append(sp(10))

    # 2. 최초 설정
    story.append(Paragraph("2.  최초 GitHub 저장소 연결 (한 번만)", S["h1"]))
    story.append(hr())
    story.append(info_box(
        "GitHub 계정이 없으면 https://github.com 에서 먼저 가입하세요.\n"
        "Git이 설치되어 있지 않으면 https://git-scm.com 에서 설치하세요.",
        bg=C_LAMBER, fg=C_AMBER,
    ))
    story.append(sp(6))

    story.append(step_box(1, "GitHub에서 새 저장소(Repository) 생성", [
        "github.com 로그인 → 우상단 [+] → New repository",
        "Repository name 입력 (예: specimen-routing)",
        "Private 선택 (내부 업무용) → Create repository",
        "생성 후 화면의 저장소 주소를 복사 (예: https://github.com/ID/specimen-routing.git)",
    ]))
    story.append(step_box(2, "로컬 폴더를 GitHub에 연결 (Git Bash 또는 터미널)", [
        "C:\\Build\\Specimen 폴더에서 아래 명령을 순서대로 실행합니다.",
    ]))
    cmd1 = Table([[Paragraph(
        "git init\n"
        "git add -A\n"
        'git commit -m "initial commit"\n'
        "git branch -M main\n"
        "git remote add origin https://github.com/계정명/저장소명.git\n"
        "git push -u origin main",
        ParagraphStyle("cmd", fontName="Malgun", fontSize=9,
                       textColor=colors.HexColor("#1e3a5f"), leading=16,
                       leftIndent=4),
    )]], colWidths=[150*mm])
    cmd1.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f0f4ff")),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(cmd1)
    story.append(sp(4))
    story.append(info_box(
        "✅  push 후 GitHub 저장소 페이지를 새로 고침하면 파일이 보입니다.\n"
        "     python\\ 폴더와 .db 파일은 .gitignore에 의해 자동 제외됩니다.",
        bg=C_LGREEN, fg=C_GREEN,
    ))
    story.append(sp(10))

    # 3. 코드 수정 후 배포
    story.append(Paragraph("3.  코드 수정 후 새 버전 배포", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "코드를 수정할 때마다 아래 순서를 따릅니다.", S["body"]))
    story.append(sp(6))

    story.append(step_box(1, "파일 수정 후 변경 사항 저장·커밋", [
        "app\\ 폴더의 파일을 수정합니다.",
        "Git Bash에서 아래 명령 실행:",
    ]))
    cmd2 = Table([[Paragraph(
        "git add -A\n"
        'git commit -m "fix: 소분류 리셋 버튼 추가"',
        ParagraphStyle("cmd", fontName="Malgun", fontSize=9,
                       textColor=colors.HexColor("#1e3a5f"), leading=16, leftIndent=4),
    )]], colWidths=[150*mm])
    cmd2.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f0f4ff")),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(cmd2)
    story.append(sp(4))

    story.append(step_box(2, "main 브랜치에 푸시", [
        "git push origin main",
    ]))

    story.append(step_box(3, "버전 태그 생성 → GitHub Actions 자동 실행", [
        "태그를 푸시하면 GitHub Actions가 배포 ZIP을 자동 빌드합니다.",
        "버전 번호는 v숫자.숫자.숫자 형식을 사용하세요.",
    ]))
    cmd3 = Table([[Paragraph(
        "git tag v1.2.0\n"
        "git push origin v1.2.0",
        ParagraphStyle("cmd", fontName="Malgun", fontSize=9,
                       textColor=colors.HexColor("#1e3a5f"), leading=16, leftIndent=4),
    )]], colWidths=[150*mm])
    cmd3.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#f0f4ff")),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(cmd3)
    story.append(sp(4))

    story.append(step_box(4, "GitHub Actions 빌드 완료 확인 (약 5~10분 소요)", [
        "GitHub 저장소 → Actions 탭 → 가장 최근 워크플로우 클릭",
        "초록색 체크 표시가 나타나면 성공입니다.",
        "Releases 탭에 새 버전이 자동으로 생성됩니다.",
    ]))
    story.append(sp(10))

    # 4. GitHub Actions 워크플로우 설명
    story.append(Paragraph("4.  GitHub Actions 워크플로우 설명", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "워크플로우 파일 위치:  .github\\workflows\\release.yml", S["code"]))
    story.append(sp(6))

    wf_rows = [
        ["단계", "설명"],
        ["Checkout",           "GitHub에서 소스 코드 내려받기"],
        ["Setup embedded Python", "python.org에서 Python 3.11 임베디드 패키지 다운로드\n"
                                  "pip 설치 → requirements.txt 패키지 일괄 설치"],
        ["Generate PDF docs",  "make_docs.py 실행 → 문서 PDF 4종 생성"],
        ["Build deployment ZIPs", "app\\ + python\\ + 런처 파일 + PDF 묶어서 ZIP 2종 생성"],
        ["Create GitHub Release", "ZIP 2종을 Releases 페이지에 자동 업로드\n"
                                   "릴리즈 노트(설치 방법 등) 자동 생성"],
    ]
    wt = Table(wf_rows, colWidths=[45*mm, 105*mm])
    wt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(wt)
    story.append(sp(10))

    # 5. 버전 관리 규칙
    story.append(Paragraph("5.  버전 번호 규칙 (권장)", S["h1"]))
    story.append(hr())

    ver_rows = [
        ["버전 형식", "사용 시점", "예시"],
        ["v X.0.0  (Major)", "전체 구조 변경, 하위 호환 불가", "v2.0.0"],
        ["v X.Y.0  (Minor)", "새 기능 추가 (소분류 리셋, TTS 등)", "v1.3.0"],
        ["v X.Y.Z  (Patch)", "버그 수정, 텍스트 수정 등 소규모 수정", "v1.2.1"],
    ]
    vt = Table(ver_rows, colWidths=[38*mm, 72*mm, 40*mm])
    vt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(vt)
    story.append(sp(6))
    story.append(info_box(
        "❗  태그는 삭제하지 마세요. 한 번 배포된 버전은 사용자가 내려받았을 수 있습니다.\n"
        "    수정이 필요하면 다음 버전(예: v1.2.1)으로 새로 배포하세요.",
        bg=C_LRED, fg=C_RED,
    ))

    return story


# ═══════════════════════════════════════════════════════════════════════
#  PDF 4: GitHub 다운로드 안내서 (초보 사용자용)
# ═══════════════════════════════════════════════════════════════════════
def github_download_guide():
    story = []

    story.append(sp(30))
    story.append(cover_table(
        "검체관리프로그램",
        "GitHub에서 프로그램 다운로드 안내서 (초보자용)",
    ))
    story.append(sp(12))
    story.append(info_box(
        "이 안내서는 GitHub에서 프로그램을 처음 내려받는 분을 위한 안내서입니다.\n"
        "GitHub 계정 없이도 무료로 다운로드할 수 있습니다.",
        bg=C_LGREEN, fg=C_GREEN,
    ))
    story.append(PageBreak())

    # 1. 준비
    story.append(Paragraph("1.  시작 전 확인", S["h1"]))
    story.append(hr())
    story.append(Paragraph(
        "아래 세 가지만 확인하면 됩니다. 파이썬·개발 도구는 전혀 필요 없습니다.",
        S["body"]))
    story.append(sp(6))
    pre = [
        ["✅  인터넷 연결",   "ZIP 파일을 내려받을 때만 필요합니다.\n설치 후에는 인터넷 없이 사용 가능합니다."],
        ["✅  Windows 10/11", "Windows 10 64비트 또는 Windows 11 이상"],
        ["✅  200 MB 여유 공간", "ZIP 압축 해제 후 약 200 MB 필요합니다."],
    ]
    pt = Table(pre, colWidths=[42*mm, 108*mm])
    pt.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("FONTNAME",      (0,0), (0,-1), "MalgunBd"),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [C_LGREEN, colors.white]),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(pt)
    story.append(sp(10))

    # 2. GitHub 접속
    story.append(Paragraph("2.  GitHub에서 프로그램 다운로드", S["h1"]))
    story.append(hr())

    story.append(step_box(1, "Chrome 또는 Edge 브라우저를 엽니다", [
        "바탕화면 또는 작업 표시줄의 브라우저 아이콘을 클릭합니다.",
    ]))

    story.append(step_box(2, "관리자에게 받은 GitHub 주소로 이동합니다", [
        "브라우저 주소창(상단 긴 막대)에 주소를 입력하고 Enter를 누릅니다.",
        "예)  https://github.com/계정명/specimen-routing",
        "주소를 모르면 관리자에게 문의하세요.",
    ]))

    story.append(step_box(3, "Releases(릴리즈) 페이지로 이동합니다", [
        "저장소 페이지 오른쪽 하단에서 'Releases' 또는 'Latest' 를 클릭합니다.",
        "또는 주소창에  .../releases/latest  를 직접 입력해도 됩니다.",
    ]))

    url_box = Table([[Paragraph(
        "https://github.com/계정명/specimen-routing/releases/latest",
        ParagraphStyle("url", fontName="Malgun", fontSize=10,
                       textColor=C_BLUE, leading=14),
    )]], colWidths=[150*mm])
    url_box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_LBLUE),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(url_box)
    story.append(sp(8))

    story.append(step_box(4, "Assets에서 ZIP 파일을 클릭해 다운로드합니다", [
        "페이지 아래쪽 'Assets' 섹션을 찾습니다.",
        "아래 파일 중 '설치' 파일을 클릭합니다.",
    ]))

    dl_rows = [
        ["파일명", "크기", "선택 기준"],
        ["검체관리프로그램_설치_vX.X.X.zip", "약 60 MB",
         "처음 설치하는 PC → 이 파일을 받으세요"],
        ["검체관리프로그램_업데이트_vX.X.X.zip", "약 0.1 MB",
         "이미 설치된 PC에서 업데이트할 때만"],
    ]
    dlt = Table(dl_rows, colWidths=[62*mm, 20*mm, 68*mm])
    dlt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#374151")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "MalgunBd"),
        ("FONTNAME",      (0,1), (-1,-1), "Malgun"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("BACKGROUND",    (0,1), (-1,1), C_LGREEN),
        ("BACKGROUND",    (0,2), (-1,2), colors.white),
        ("GRID",          (0,0), (-1,-1), 0.4, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(dlt)
    story.append(sp(6))
    story.append(info_box(
        "💡  다운로드 중 '이 파일은 안전하지 않을 수 있습니다' 경고가 나타날 수 있습니다.\n"
        "     '저장' 또는 '유지'를 클릭해서 계속 진행하세요.",
        bg=C_LAMBER, fg=C_AMBER,
    ))
    story.append(sp(10))

    # 3. 압축 해제 및 설치
    story.append(Paragraph("3.  ZIP 압축 해제 및 설치", S["h1"]))
    story.append(hr())

    story.append(step_box(1, "내려받은 ZIP 파일을 원하는 위치로 이동합니다", [
        "권장 위치: 바탕화면 또는 D드라이브",
        "⚠  C:\\Program Files 안에는 넣지 마세요 (권한 문제가 발생할 수 있습니다).",
    ]))
    story.append(step_box(2, "ZIP 파일을 우클릭 → '모두 압축 풀기' 클릭", [
        "ZIP 파일에서 마우스 오른쪽 버튼을 클릭합니다.",
        "메뉴에서 '모두 압축 풀기(T)...' 를 선택합니다.",
        "'압축 풀기' 버튼을 클릭합니다.",
        "완료되면 '검체관리프로그램' 폴더가 생성됩니다.",
    ]))
    story.append(step_box(3, "'시작.bat' 파일을 더블클릭합니다", [
        "'검체관리프로그램' 폴더를 열면 '시작.bat' 파일이 있습니다.",
        "더블클릭하면 검은 콘솔 창이 잠깐 뜨고, 4~10초 후 브라우저가 자동으로 열립니다.",
        "브라우저 주소창에 http://localhost:8000 이 표시되면 성공입니다.",
    ]))
    story.append(sp(6))
    story.append(info_box(
        "✅  설치 완료! 앞으로는 '시작.bat'을 더블클릭하기만 하면 됩니다.\n"
        "     바탕화면 바로 가기를 만들어두면 더 편리합니다.\n"
        "     (시작.bat 우클릭 → 바로 가기 만들기 → 바탕화면으로 이동)",
        bg=C_LGREEN, fg=C_GREEN,
    ))
    story.append(sp(10))

    # 4. 문제 해결
    story.append(Paragraph("4.  자주 묻는 질문", S["h1"]))
    story.append(hr())

    faqs = [
        ("Q.  'Windows의 PC 보호' 또는 '알 수 없는 앱' 경고가 뜹니다.",
         "'추가 정보'를 클릭한 후 '실행' 버튼을 누르세요.\n"
         "이 프로그램은 인터넷 연결 없이 내 PC 안에서만 동작하는 안전한 프로그램입니다."),
        ("Q.  백신(보안 프로그램)이 차단합니다.",
         "백신의 '예외 목록' 또는 '허용 목록'에 '검체관리프로그램' 폴더를 추가하세요.\n"
         "방법을 모르면 IT 담당자 또는 관리자에게 문의하세요."),
        ("Q.  브라우저가 자동으로 열리지 않습니다.",
         "Chrome 또는 Edge를 직접 열고\n"
         "주소창에 http://localhost:8000 을 입력하고 Enter를 누르세요."),
        ("Q.  프로그램을 종료하려면?",
         "시작.bat을 실행한 검은 콘솔 창을 닫으면 서버도 함께 종료됩니다."),
        ("Q.  새 버전이 나왔다는 안내를 받았습니다.",
         "관리자에게 업데이트 ZIP 파일(검체관리프로그램_업데이트_*.zip)을 받아서\n"
         "'검체관리프로그램' 폴더 안의 'app' 폴더만 교체하면 됩니다.\n"
         "데이터베이스(specimen_routing.db)는 건드리지 마세요."),
    ]
    for q, a in faqs:
        qbox = Table(
            [[Paragraph(q, ParagraphStyle("q", fontName="MalgunBd", fontSize=9.5,
                                          textColor=C_BLUE))],
             [Paragraph(a, ParagraphStyle("a", fontName="Malgun", fontSize=9.5,
                                          textColor=C_DARK, leading=15, leftIndent=8))]],
            colWidths=[150*mm],
        )
        qbox.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), C_LBLUE),
            ("BACKGROUND",    (0,1), (-1,1), colors.white),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LINEBELOW",     (0,-1), (-1,-1), 0.3, C_LINE),
        ]))
        story.append(qbox)
        story.append(sp(4))

    return story


# ── 실행 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    out_dir = Path(__file__).parent / "배포" / "문서"
    out_dir.mkdir(parents=True, exist_ok=True)

    docs = [
        ("설치_안내서.pdf",            user_guide,              "초보 사용자 설치·사용 안내서"),
        ("관리자_안내서.pdf",           admin_guide,             "관리자 파일 기능·운영 안내서"),
        ("GitHub_관리자_안내서.pdf",    github_admin_guide,      "GitHub 배포 관리 안내서"),
        ("GitHub_다운로드_안내서.pdf",  github_download_guide,   "GitHub 다운로드 초보자 안내서"),
    ]

    for i, (fname, fn, label) in enumerate(docs, 1):
        path = str(out_dir / fname)
        print(f"  [{i}/{len(docs)}] {label} 생성 중...")
        build_doc(path, fn)
        print(f"         -> {path}")

    print("\n완료! 총 4개 PDF 생성됨")
