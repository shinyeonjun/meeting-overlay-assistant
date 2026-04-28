"""ReportDocumentV1 기반 회의록 PDF writer."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)
from server.app.services.reports.composition.report_document_projection import (
    resolve_agenda_text,
    resolve_action_items,
    resolve_decision_items,
    resolve_flat_discussion_items,
    resolve_special_note_items,
    section_discussion_groups,
    section_discussion_items,
    sections_with_discussion,
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
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
            "minutes_section_title": ParagraphStyle(
                "DocumentMinutesSectionTitle",
                fontName=bold_font_name,
                fontSize=10,
                leading=13,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#1F252D"),
                spaceBefore=6,
                spaceAfter=6,
            ),
            "field_label": ParagraphStyle(
                "DocumentFieldLabel",
                fontName=bold_font_name,
                fontSize=9,
                leading=13,
                alignment=TA_CENTER,
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
            "discussion_group_label": ParagraphStyle(
                "DocumentDiscussionGroupLabel",
                fontName=bold_font_name,
                fontSize=8.8,
                leading=12,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#344054"),
                spaceBefore=3,
                spaceAfter=1,
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

    story: list[object] = [
        Spacer(1, 4),
        Paragraph("회의록", styles["document_title"]),
        HRFlowable(width="100%", thickness=1.1, color=colors.HexColor("#AEB4BD")),
        Spacer(1, 6),
        Paragraph("1. 회의개요", styles["minutes_section_title"]),
        _build_metadata_table(document, styles, content_width),
        Spacer(1, 6),
        Paragraph("2. 회의내용", styles["minutes_section_title"]),
    ]
    story.extend(_build_discussion_section(document, styles, content_width))
    story.extend(
        _build_list_item_section(
            "결정사항",
            resolve_decision_items(document),
            styles,
            content_width,
        )
    )
    story.extend(
        _build_action_section(resolve_action_items(document), styles, content_width)
    )
    story.extend(
        _build_list_item_section(
            "특이사항",
            resolve_special_note_items(document),
            styles,
            content_width,
        )
    )
    return story


def _build_metadata_table(
    document: ReportDocumentV1,
    styles: dict[str, object],
    content_width: float,
):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    fields = document.metadata
    meeting_datetime = _metadata_value(fields, "일시") or ""
    location = _metadata_value(fields, "장소") or _metadata_value(fields, "회의장소") or ""
    writer = (
        _metadata_value(fields, "작성자")
        or _metadata_value(fields, "회의 주최자")
        or ""
    )
    written_date = _metadata_value(fields, "작성일") or _date_part(meeting_datetime)
    participants = _metadata_value(fields, "참석자") or ""
    agenda = resolve_agenda_text(document)
    rows = [
        [
            Paragraph("일시", styles["meta_label"]),
            Paragraph(_escape(meeting_datetime), styles["meta_value"]),
            Paragraph("장소", styles["meta_label"]),
            Paragraph(_escape(location), styles["meta_value"]),
        ],
        [
            Paragraph("작성자", styles["meta_label"]),
            Paragraph(_escape(writer), styles["meta_value"]),
            Paragraph("작성일", styles["meta_label"]),
            Paragraph(_escape(written_date), styles["meta_value"]),
        ],
        [
            Paragraph("참석자", styles["meta_label"]),
            Paragraph(_escape(participants), styles["meta_value"]),
            "",
            "",
        ],
        [
            Paragraph("안건", styles["meta_label"]),
            Paragraph(_escape(agenda), styles["meta_value"]),
            "",
            "",
        ],
    ]

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
                ("SPAN", (1, 2), (-1, 2)),
                ("SPAN", (1, 3), (-1, 3)),
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

    body: list[object] = []
    if not items:
        body.append(Paragraph("기록된 내용이 없습니다.", styles["empty"]))
    else:
        for index, item in enumerate(items, start=1):
            body.append(
                Paragraph(f"{index}. {_escape(item.text)}", styles["item_text"])
            )
    return [
        _build_content_field_table(
            title,
            body,
            styles,
            content_width,
            min_height=_field_min_height(title),
        ),
        Spacer(1, 0),
    ]


def _build_discussion_section(
    document: ReportDocumentV1,
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    from reportlab.platypus import Paragraph, Spacer

    body: list[object] = []
    if not document.sections:
        items = resolve_flat_discussion_items(document)
        if not items:
            body.append(Paragraph("기록된 내용이 없습니다.", styles["empty"]))
        else:
            for index, item in enumerate(items, start=1):
                body.append(
                    Paragraph(f"{index}. {_escape(item.text)}", styles["item_text"])
                )
    else:
        sections = sections_with_discussion(document)
        if not sections:
            items = resolve_flat_discussion_items(document)
            if not items:
                body.append(Paragraph("기록된 내용이 없습니다.", styles["empty"]))
            else:
                for index, item in enumerate(items, start=1):
                    body.append(
                        Paragraph(f"{index}. {_escape(item.text)}", styles["item_text"])
                    )
        else:
            for section_index, section in enumerate(sections, start=1):
                body.append(
                    Paragraph(
                        f"{section_index}. {_escape(section.title)}",
                        styles["item_text"],
                    )
                )
                groups = section_discussion_groups(section)
                if groups:
                    for label, items in groups:
                        body.append(
                            Paragraph(_escape(label), styles["discussion_group_label"])
                        )
                        for item in items:
                            body.append(
                                Paragraph(f"- {_escape(item.text)}", styles["table_body"])
                            )
                    continue
                for item in section_discussion_items(section):
                    body.append(
                        Paragraph(f"- {_escape(item.text)}", styles["table_body"])
                    )

    return [
        _build_content_field_table(
            "회의내용",
            body,
            styles,
            content_width,
            min_height=_field_min_height("회의내용"),
        ),
        Spacer(1, 0),
    ]


def _build_action_section(
    items: tuple[ReportActionItem, ...],
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    from reportlab.platypus import Paragraph, Spacer

    body: list[object] = []
    if not items:
        body.append(Paragraph("기록된 향후일정이 없습니다.", styles["empty"]))
    else:
        for index, item in enumerate(items, start=1):
            body.append(
                Paragraph(f"{index}. {_escape(item.task)}", styles["item_text"])
            )
    return [
        _build_content_field_table(
            "향후일정",
            body,
            styles,
            content_width,
            min_height=_field_min_height("향후일정"),
        ),
        Spacer(1, 0),
    ]


def _metadata_value(fields: tuple[ReportMetaField, ...], label: str) -> str | None:
    for field in fields:
        if field.label == label:
            return field.value
    return None


def _date_part(value: str) -> str:
    parts = value.split()
    return parts[0] if parts else ""


def _build_content_field_table(
    title: str,
    body: list[object],
    styles: dict[str, object],
    content_width: float,
    *,
    min_height: int = 0,
):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    body_items = list(body)
    if min_height and len(body_items) == 1:
        body_items.append(Spacer(1, min_height))

    table = Table(
        [[Paragraph(_escape(title), styles["field_label"]), body_items]],
        colWidths=[content_width * 0.17, content_width * 0.83],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (0, -1), "MIDDLE"),
                ("VALIGN", (1, 0), (1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F1F3")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6D9DE")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#AEB4BD")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _field_min_height(title: str) -> int:
    return {
        "안건": 28,
        "회의내용": 64,
        "결정사항": 22,
        "특이사항": 22,
        "향후일정": 22,
    }.get(title, 24)


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


def _escape(value: str) -> str:
    return escape(str(value), {"\n": "<br/>"})
