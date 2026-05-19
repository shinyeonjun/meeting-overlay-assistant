"""회의록 PDF 전용 ReportLab 스타일 정의."""

from __future__ import annotations

from server.app.services.reports.composition.pdf_writer.reportlab_helpers import (
    build_report_styles,
)


def build_document_pdf_styles() -> dict[str, object]:
    """회의록 PDF 문서에 필요한 ReportLab 스타일을 만든다."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle

    base_styles = build_report_styles()
    regular_font_name = base_styles["body"].fontName
    bold_font_name = base_styles["title"].fontName

    styles: dict[str, object] = dict(base_styles)
    styles.update(
        _build_document_header_styles(
            ParagraphStyle,
            colors,
            regular_font_name=regular_font_name,
            bold_font_name=bold_font_name,
            center_alignment=TA_CENTER,
        )
    )
    styles.update(
        _build_document_section_styles(
            ParagraphStyle,
            colors,
            bold_font_name=bold_font_name,
            left_alignment=TA_LEFT,
        )
    )
    styles.update(
        _build_document_metadata_styles(
            ParagraphStyle,
            colors,
            regular_font_name=regular_font_name,
            bold_font_name=bold_font_name,
            center_alignment=TA_CENTER,
            left_alignment=TA_LEFT,
        )
    )
    styles.update(
        _build_document_item_styles(
            ParagraphStyle,
            colors,
            regular_font_name=regular_font_name,
            left_alignment=TA_LEFT,
        )
    )
    styles.update(
        _build_document_discussion_styles(
            ParagraphStyle,
            colors,
            regular_font_name=regular_font_name,
            bold_font_name=bold_font_name,
            left_alignment=TA_LEFT,
        )
    )
    return styles


def _build_document_header_styles(
    paragraph_style,
    colors,
    *,
    regular_font_name: str,
    bold_font_name: str,
    center_alignment: int,
) -> dict[str, object]:
    return {
        "kicker": paragraph_style(
            "DocumentKicker",
            fontName=bold_font_name,
            fontSize=8,
            leading=11,
            alignment=center_alignment,
            textColor=colors.HexColor("#667085"),
            spaceAfter=8,
        ),
        "document_title": paragraph_style(
            "DocumentTitle",
            fontName=bold_font_name,
            fontSize=23,
            leading=28,
            alignment=center_alignment,
            textColor=colors.HexColor("#111827"),
            spaceAfter=8,
        ),
        "generated_at": paragraph_style(
            "DocumentGeneratedAt",
            fontName=regular_font_name,
            fontSize=8.5,
            leading=12,
            alignment=center_alignment,
            textColor=colors.HexColor("#667085"),
            spaceAfter=8,
        ),
    }


def _build_document_section_styles(
    paragraph_style,
    colors,
    *,
    bold_font_name: str,
    left_alignment: int,
) -> dict[str, object]:
    return {
        "section_bar": paragraph_style(
            "DocumentSectionBar",
            fontName=bold_font_name,
            fontSize=9.5,
            leading=12,
            alignment=left_alignment,
            textColor=colors.HexColor("#20242A"),
        ),
        "minutes_section_title": paragraph_style(
            "DocumentMinutesSectionTitle",
            fontName=bold_font_name,
            fontSize=10,
            leading=13,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F252D"),
            spaceBefore=6,
            spaceAfter=6,
        ),
    }


def _build_document_metadata_styles(
    paragraph_style,
    colors,
    *,
    regular_font_name: str,
    bold_font_name: str,
    center_alignment: int,
    left_alignment: int,
) -> dict[str, object]:
    return {
        "field_label": paragraph_style(
            "DocumentFieldLabel",
            fontName=bold_font_name,
            fontSize=9,
            leading=13,
            alignment=center_alignment,
            textColor=colors.HexColor("#20242A"),
        ),
        "meta_label": paragraph_style(
            "DocumentMetaLabel",
            fontName=bold_font_name,
            fontSize=8.3,
            leading=11,
            alignment=center_alignment,
            textColor=colors.HexColor("#344054"),
        ),
        "meta_value": paragraph_style(
            "DocumentMetaValue",
            fontName=regular_font_name,
            fontSize=8.8,
            leading=12,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F252D"),
        ),
        "table_header": paragraph_style(
            "DocumentTableHeader",
            fontName=bold_font_name,
            fontSize=8.3,
            leading=11,
            alignment=center_alignment,
            textColor=colors.HexColor("#344054"),
        ),
        "table_body": paragraph_style(
            "DocumentTableBody",
            fontName=regular_font_name,
            fontSize=8.2,
            leading=11.5,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F252D"),
        ),
    }


def _build_document_item_styles(
    paragraph_style,
    colors,
    *,
    regular_font_name: str,
    left_alignment: int,
) -> dict[str, object]:
    return {
        "item_text": paragraph_style(
            "DocumentItemText",
            fontName=regular_font_name,
            fontSize=9.2,
            leading=13.8,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F252D"),
            spaceAfter=1,
        ),
        "item_meta": paragraph_style(
            "DocumentItemMeta",
            fontName=regular_font_name,
            fontSize=8.4,
            leading=11.5,
            alignment=left_alignment,
            textColor=colors.HexColor("#667085"),
            spaceAfter=4,
        ),
        "empty": paragraph_style(
            "DocumentEmpty",
            fontName=regular_font_name,
            fontSize=9,
            leading=13,
            alignment=left_alignment,
            textColor=colors.HexColor("#667085"),
            spaceAfter=6,
        ),
    }


def _build_document_discussion_styles(
    paragraph_style,
    colors,
    *,
    regular_font_name: str,
    bold_font_name: str,
    left_alignment: int,
) -> dict[str, object]:
    return {
        "section_heading": paragraph_style(
            "DocumentSectionHeading",
            fontName=bold_font_name,
            fontSize=10.2,
            leading=14.5,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F252D"),
            spaceBefore=3,
            spaceAfter=2,
        ),
        "discussion_group_label": paragraph_style(
            "DocumentDiscussionGroupLabel",
            fontName=bold_font_name,
            fontSize=8.8,
            leading=12,
            alignment=left_alignment,
            textColor=colors.HexColor("#344054"),
            spaceBefore=3,
            spaceAfter=1,
        ),
        "discussion_bullet": paragraph_style(
            "DocumentDiscussionBullet",
            fontName=regular_font_name,
            fontSize=9.1,
            leading=13.4,
            alignment=left_alignment,
            textColor=colors.HexColor("#1F252D"),
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
    }
