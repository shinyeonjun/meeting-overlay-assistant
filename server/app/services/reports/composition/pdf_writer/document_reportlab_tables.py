"""ReportLab 회의록 표 생성 helper."""

from __future__ import annotations

from xml.sax.saxutils import escape

from server.app.services.reports.composition.inline_formatting import render_reportlab_inline
from server.app.services.reports.composition.report_document import (
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)
from server.app.services.reports.composition.report_document_projection import (
    resolve_agenda_text,
)


def build_metadata_table(
    document: ReportDocumentV1,
    styles: dict[str, object],
    content_width: float,
):
    from reportlab.platypus import Table

    table = Table(
        _build_metadata_rows(document, styles),
        colWidths=_metadata_col_widths(content_width),
        hAlign="LEFT",
    )
    table.setStyle(_metadata_table_style())
    return table


def _build_metadata_rows(
    document: ReportDocumentV1,
    styles: dict[str, object],
) -> list[list[object]]:
    from reportlab.platypus import Paragraph

    values = _metadata_values(document)
    return [
        _metadata_row("회의제목", values["meeting_title"], styles),
        _metadata_row("일시", values["meeting_datetime"], styles, "장소", values["location"]),
        _metadata_row("작성자", values["writer"], styles, "작성일", values["written_date"]),
        _metadata_row("참석자", values["participants"], styles),
        _metadata_row("안건", values["agenda"], styles),
    ]


def _metadata_values(document: ReportDocumentV1) -> dict[str, str]:
    fields = document.metadata
    meeting_title = (
        metadata_value(fields, "회의제목")
        or (
            document.title
            if document.title.strip() and document.title.strip() != "회의록"
            else ""
        )
    )
    meeting_datetime = metadata_value(fields, "일시") or ""
    return {
        "meeting_title": meeting_title,
        "meeting_datetime": meeting_datetime,
        "location": metadata_value(fields, "장소")
        or metadata_value(fields, "회의장소")
        or "",
        "writer": metadata_value(fields, "작성자")
        or metadata_value(fields, "회의 주최자")
        or "",
        "written_date": metadata_value(fields, "작성일") or date_part(meeting_datetime),
        "participants": metadata_value(fields, "참석자") or "",
        "agenda": resolve_agenda_text(document),
    }


def _metadata_row(
    left_label: str,
    left_value: str,
    styles: dict[str, object],
    right_label: str = "",
    right_value: str = "",
) -> list[object]:
    from reportlab.platypus import Paragraph

    row: list[object] = [
        Paragraph(left_label, styles["meta_label"]),
        Paragraph(escape_reportlab_text(left_value), styles["meta_value"]),
    ]
    if not right_label:
        return [*row, "", ""]
    return [
        *row,
        Paragraph(right_label, styles["meta_label"]),
        Paragraph(escape_reportlab_text(right_value), styles["meta_value"]),
    ]


def _metadata_col_widths(content_width: float) -> list[float]:
    return [
        content_width * 0.17,
        content_width * 0.33,
        content_width * 0.17,
        content_width * 0.33,
    ]


def _metadata_table_style():
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    return TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F1F3")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F0F1F3")),
            ("BACKGROUND", (1, 0), (-1, 0), colors.white),
            ("BACKGROUND", (1, 3), (-1, 3), colors.white),
            ("BACKGROUND", (1, 4), (-1, 4), colors.white),
            ("SPAN", (1, 0), (-1, 0)),
            ("SPAN", (1, 3), (-1, 3)),
            ("SPAN", (1, 4), (-1, 4)),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6D9DE")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#AEB4BD")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )


def build_content_field_table(
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
        [[Paragraph(escape_reportlab_text(title), styles["field_label"]), body_items]],
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


def field_min_height(title: str) -> int:
    return {
        "안건": 28,
        "회의내용": 64,
        "결정사항": 22,
        "특이사항": 22,
        "향후일정": 22,
    }.get(title, 24)


def metadata_value(fields: tuple[ReportMetaField, ...], label: str) -> str | None:
    for field in fields:
        if field.label == label:
            return field.value
    return None


def date_part(value: str) -> str:
    parts = value.split()
    return parts[0] if parts else ""


def escape_reportlab_text(value: str) -> str:
    return escape(str(value), {"\n": "<br/>"})


def escape_list_item_text(item: ReportListItem) -> str:
    return render_reportlab_inline(item.text, item.important_phrases)
