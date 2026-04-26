"""ReportDocumentV1 기반 회의록 PDF writer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from server.app.services.reports.composition.html_report_template import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)
from server.app.services.reports.composition.pdf_writer.reportlab_helpers import (
    build_report_styles,
    draw_page_chrome,
)


def write_report_document_pdf(*, output_path: Path, document: ReportDocumentV1) -> None:
    """정본 회의록 문서를 고정 양식 PDF로 저장한다."""

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate

    left_margin = 48
    right_margin = 48
    page_width, _ = A4
    content_width = page_width - left_margin - right_margin
    styles = build_document_pdf_styles()
    story = build_document_pdf_story(
        document=document,
        styles=styles,
        content_width=content_width,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=42,
        bottomMargin=36,
        title=document.title,
        author="CAPS",
    )
    doc.build(
        story,
        onFirstPage=draw_page_chrome,
        onLaterPages=draw_page_chrome,
    )


def build_document_pdf_styles() -> dict[str, object]:
    """문서형 회의록 PDF에 필요한 ReportLab 스타일을 만든다."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.styles import ParagraphStyle

    base_styles = build_report_styles()
    regular_font_name = base_styles["body"].fontName
    bold_font_name = base_styles["title"].fontName

    styles: dict[str, object] = dict(base_styles)
    styles.update(
        {
            "kicker": ParagraphStyle(
                "DocumentKicker",
                fontName=bold_font_name,
                fontSize=8,
                leading=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#667085"),
                spaceAfter=8,
            ),
            "document_title": ParagraphStyle(
                "DocumentTitle",
                fontName=bold_font_name,
                fontSize=23,
                leading=28,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#111827"),
                spaceAfter=8,
            ),
            "generated_at": ParagraphStyle(
                "DocumentGeneratedAt",
                fontName=regular_font_name,
                fontSize=8.5,
                leading=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#667085"),
                spaceAfter=8,
            ),
            "section_bar": ParagraphStyle(
                "DocumentSectionBar",
                fontName=bold_font_name,
                fontSize=9.5,
                leading=12,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#20242A"),
            ),
            "meta_label": ParagraphStyle(
                "DocumentMetaLabel",
                fontName=bold_font_name,
                fontSize=8.3,
                leading=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#344054"),
            ),
            "meta_value": ParagraphStyle(
                "DocumentMetaValue",
                fontName=regular_font_name,
                fontSize=8.8,
                leading=12,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#1F252D"),
            ),
            "item_text": ParagraphStyle(
                "DocumentItemText",
                fontName=bold_font_name,
                fontSize=10,
                leading=14.5,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#1F252D"),
                spaceAfter=1,
            ),
            "item_meta": ParagraphStyle(
                "DocumentItemMeta",
                fontName=regular_font_name,
                fontSize=8.4,
                leading=11.5,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#667085"),
                spaceAfter=4,
            ),
            "empty": ParagraphStyle(
                "DocumentEmpty",
                fontName=regular_font_name,
                fontSize=9,
                leading=13,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#667085"),
                spaceAfter=6,
            ),
            "table_header": ParagraphStyle(
                "DocumentTableHeader",
                fontName=bold_font_name,
                fontSize=8.3,
                leading=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#344054"),
            ),
            "table_body": ParagraphStyle(
                "DocumentTableBody",
                fontName=regular_font_name,
                fontSize=8.2,
                leading=11.5,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#1F252D"),
            ),
        }
    )
    return styles


def build_document_pdf_story(
    *,
    document: ReportDocumentV1,
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    """ReportDocumentV1을 ReportLab story로 변환한다."""

    from reportlab.lib import colors
    from reportlab.platypus import HRFlowable, Paragraph, Spacer

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    story: list[object] = [
        Spacer(1, 4),
        Paragraph("CAPS MEETING REPORT", styles["kicker"]),
        Paragraph(_escape(document.title), styles["document_title"]),
        Paragraph(f"생성 시각: {generated_at}", styles["generated_at"]),
        HRFlowable(width="100%", thickness=1.1, color=colors.HexColor("#AEB4BD")),
        Spacer(1, 6),
        _build_metadata_table(document.metadata, styles, content_width),
        Spacer(1, 6),
    ]
    story.extend(_build_text_section("회의내용", document.summary, styles, content_width))
    story.extend(
        _build_list_item_section("의결사항", document.decisions, styles, content_width)
    )
    story.extend(_build_action_table(document.action_items, styles, content_width))
    story.extend(
        _build_list_item_section("질문 및 확인사항", document.questions, styles, content_width)
    )
    story.extend(
        _build_list_item_section("리스크 및 이슈", document.risks, styles, content_width)
    )
    story.extend(
        _build_text_section("참고 전사", document.transcript_excerpt, styles, content_width)
    )
    if document.speaker_insights:
        story.extend(
            _build_text_section(
                "발화자 기반 인사이트",
                document.speaker_insights,
                styles,
                content_width,
            )
        )
    return story


def _build_metadata_table(
    fields: tuple[ReportMetaField, ...],
    styles: dict[str, object],
    content_width: float,
):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    rows = []
    normalized_fields = fields or (ReportMetaField("회의정보", "-"),)
    for index in range(0, len(normalized_fields), 2):
        first = normalized_fields[index]
        second = normalized_fields[index + 1] if index + 1 < len(normalized_fields) else None
        rows.append(
            [
                Paragraph(_escape(first.label), styles["meta_label"]),
                Paragraph(_escape(first.value), styles["meta_value"]),
                Paragraph(_escape(second.label), styles["meta_label"]) if second else "",
                Paragraph(_escape(second.value), styles["meta_value"]) if second else "",
            ]
        )

    table = Table(
        rows,
        colWidths=[
            content_width * 0.17,
            content_width * 0.33,
            content_width * 0.17,
            content_width * 0.33,
        ],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F1F3")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F0F1F3")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6D9DE")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#AEB4BD")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _build_text_section(
    title: str,
    items: tuple[str, ...],
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    from reportlab.platypus import Paragraph, Spacer

    story = [_build_section_bar(title, styles, content_width)]
    if not items:
        story.append(Paragraph("기록된 내용이 없습니다.", styles["empty"]))
    else:
        for index, item in enumerate(items, start=1):
            story.append(
                Paragraph(f"{index}. {_escape(item)}", styles["body"])
            )
    story.append(Spacer(1, 5))
    return story


def _build_list_item_section(
    title: str,
    items: tuple[ReportListItem, ...],
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    from reportlab.platypus import Paragraph, Spacer

    story = [_build_section_bar(title, styles, content_width)]
    if not items:
        story.append(Paragraph("기록된 내용이 없습니다.", styles["empty"]))
    else:
        for index, item in enumerate(items, start=1):
            story.append(
                Paragraph(f"{index}. {_escape(item.text)}", styles["item_text"])
            )
            meta_text = _format_item_meta(item)
            if meta_text:
                story.append(Paragraph(_escape(meta_text), styles["item_meta"]))
    story.append(Spacer(1, 5))
    return story


def _build_action_table(
    items: tuple[ReportActionItem, ...],
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    story = [_build_section_bar("회의결과", styles, content_width)]
    header = ["부서 및 작업", "담당자", "기한", "상태", "비고"]
    rows = [[Paragraph(label, styles["table_header"]) for label in header]]

    if not items:
        rows.append(
            [
                Paragraph("기록된 액션 아이템이 없습니다.", styles["table_body"]),
                "",
                "",
                "",
                "",
            ]
        )
    else:
        for item in items:
            rows.append(
                [
                    Paragraph(_escape(item.task), styles["table_body"]),
                    Paragraph(_escape(item.owner), styles["table_body"]),
                    Paragraph(_escape(item.due_date), styles["table_body"]),
                    Paragraph(_escape(item.status), styles["table_body"]),
                    Paragraph(_escape(_format_action_note(item)), styles["table_body"]),
                ]
            )

    table = Table(
        rows,
        colWidths=[
            content_width * 0.37,
            content_width * 0.13,
            content_width * 0.13,
            content_width * 0.12,
            content_width * 0.25,
        ],
        hAlign="LEFT",
        repeatRows=1,
    )
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6D9DE")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#AEB4BD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if not items:
        commands.append(("SPAN", (0, 1), (-1, 1)))
        commands.append(("ALIGN", (0, 1), (-1, 1), "CENTER"))
    table.setStyle(TableStyle(commands))
    story.extend([table, Spacer(1, 5)])
    return story


def _build_section_bar(title: str, styles: dict[str, object], content_width: float):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    table = Table(
        [[Paragraph(_escape(title), styles["section_bar"])]],
        colWidths=[content_width],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#D9D9D9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    table.spaceBefore = 5
    table.spaceAfter = 4
    return table


def _format_item_meta(item: ReportListItem) -> str:
    meta_parts = []
    if item.speaker:
        meta_parts.append(f"발화자: {item.speaker}")
    if item.time_range:
        meta_parts.append(f"근거 구간: {item.time_range}")
    if item.evidence:
        meta_parts.append(f"근거: {item.evidence}")
    return " · ".join(meta_parts)


def _format_action_note(item: ReportActionItem) -> str:
    note_parts = []
    if item.time_range:
        note_parts.append(f"근거 구간: {item.time_range}")
    if item.note:
        note_parts.append(item.note)
    return "\n".join(note_parts) if note_parts else "-"


def _escape(value: str) -> str:
    return escape(str(value), {"\n": "<br/>"})
