"""ReportLab 스타일/폰트 구성 helper."""

from __future__ import annotations

from pathlib import Path


def build_report_styles():
    """PDF 생성에 필요한 폰트와 스타일 묶음을 만든다."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    regular_font_name, bold_font_name = _register_report_fonts()
    styles = getSampleStyleSheet()
    return {
        **_build_heading_styles(
            styles=styles,
            colors=colors,
            paragraph_style=ParagraphStyle,
            regular_font_name=regular_font_name,
            bold_font_name=bold_font_name,
            center_alignment=TA_CENTER,
        ),
        **_build_body_styles(
            styles=styles,
            colors=colors,
            paragraph_style=ParagraphStyle,
            regular_font_name=regular_font_name,
            left_alignment=TA_LEFT,
        ),
    }


def _register_report_fonts() -> tuple[str, str]:
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

    return regular_font_name, bold_font_name


def _build_heading_styles(
    *,
    styles,
    colors,
    paragraph_style,
    regular_font_name: str,
    bold_font_name: str,
    center_alignment: int,
):
    return {
        "title": paragraph_style(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName=bold_font_name,
            fontSize=24,
            leading=30,
            alignment=center_alignment,
            textColor=colors.HexColor("#111827"),
            spaceAfter=10,
        ),
        "subtitle": paragraph_style(
            "ReportSubtitle",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10,
            leading=14,
            alignment=center_alignment,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=6,
        ),
        "section": paragraph_style(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName=bold_font_name,
            fontSize=15,
            leading=20,
            textColor=colors.HexColor("#111827"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "subsection": paragraph_style(
            "SubSectionTitle",
            parent=styles["Heading3"],
            fontName=bold_font_name,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=8,
            spaceAfter=6,
        ),
    }


def _build_body_styles(
    *,
    styles,
    colors,
    paragraph_style,
    regular_font_name: str,
    left_alignment: int,
):
    return {
        "body": paragraph_style(
            "ReportBody",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
        ),
        "bullet": paragraph_style(
            "ReportBullet",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=4,
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=0,
        ),
        "ordered": paragraph_style(
            "ReportOrdered",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F2937"),
            leftIndent=18,
            firstLineIndent=-12,
            spaceAfter=5,
        ),
        "meta": paragraph_style(
            "ReportMeta",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=9.5,
            leading=13,
            alignment=left_alignment,
            textColor=colors.HexColor("#6B7280"),
            leftIndent=26,
            spaceAfter=3,
        ),
        "transcript": paragraph_style(
            "TranscriptBody",
            parent=styles["BodyText"],
            fontName=regular_font_name,
            fontSize=10.5,
            leading=16,
            alignment=left_alignment,
            textColor=colors.HexColor("#374151"),
            leftIndent=12,
            backColor=colors.HexColor("#F9FAFB"),
            borderPadding=6,
            borderRadius=4,
            spaceAfter=5,
        ),
    }
