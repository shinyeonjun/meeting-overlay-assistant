"""ReportLab 스타일/폰트 구성 helper."""

from __future__ import annotations

from pathlib import Path


def build_report_styles():
    """PDF 생성에 필요한 폰트와 스타일 묶음을 만든다."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_font_name = "ReportRegular"
    bold_font_name = "ReportBold"
    regular_font_path = Path(r"C:\Windows\Fonts\malgun.ttf")
    bold_font_path = Path(r"C:\Windows\Fonts\malgunbd.ttf")

    if not regular_font_path.exists():
        raise FileNotFoundError("malgun.ttf not found")

    if regular_font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_font_name, str(regular_font_path)))
    if bold_font_path.exists() and bold_font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_font_name, str(bold_font_path)))
    if not bold_font_path.exists():
        bold_font_name = regular_font_name

    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName=bold_font_name,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=6,
        ),
        "section": ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName=bold_font_name,
            fontSize=15,
            leading=20,
            textColor=colors.HexColor("#111827"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "subsection": ParagraphStyle(
            "SubSectionTitle",
            parent=styles["Heading3"],
            fontName=bold_font_name,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=0,
        ),
        "ordered": ParagraphStyle(
            "ReportOrdered",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1F2937"),
            leftIndent=18,
            firstLineIndent=-12,
            spaceAfter=5,
        ),
        "meta": ParagraphStyle(
            "ReportMeta",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#6B7280"),
            leftIndent=26,
            spaceAfter=3,
        ),
        "transcript": ParagraphStyle(
            "TranscriptBody",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#374151"),
            leftIndent=12,
            backColor=colors.HexColor("#F9FAFB"),
            borderPadding=6,
            borderRadius=4,
            spaceAfter=5,
        ),
    }
