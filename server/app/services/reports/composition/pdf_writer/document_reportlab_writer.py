"""ReportDocumentV1 기반 회의록 PDF writer."""

from __future__ import annotations

from pathlib import Path

from server.app.services.reports.composition.inline_formatting import render_reportlab_inline
from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportSection,
)
from server.app.services.reports.composition.report_document_projection import (
    resolve_action_items,
    resolve_decision_items,
    resolve_flat_discussion_items,
    resolve_special_note_items,
    section_discussion_groups,
    section_discussion_items,
    sections_with_discussion,
)
from server.app.services.reports.composition.pdf_writer.document_reportlab_styles import (
    build_document_pdf_styles,
)
from server.app.services.reports.composition.pdf_writer.document_reportlab_tables import (
    build_content_field_table,
    build_metadata_table,
    escape_list_item_text,
    escape_reportlab_text,
    field_min_height,
)
from server.app.services.reports.composition.pdf_writer.reportlab_helpers import (
    draw_page_chrome,
)


def write_report_document_pdf(*, output_path: Path, document: ReportDocumentV1) -> None:
    """정본 회의록 문서를 고정 양식 PDF로 저장한다."""

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate

    left_margin = 56.7
    right_margin = 56.7
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
        topMargin=56.7,
        bottomMargin=28.35,
        title=document.title,
        author="CAPS",
    )
    doc.build(
        story,
        onFirstPage=draw_page_chrome,
        onLaterPages=draw_page_chrome,
    )


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
        build_metadata_table(document, styles, content_width),
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
                Paragraph(f"{index}. {escape_list_item_text(item)}", styles["item_text"])
            )
    return [
        build_content_field_table(
            title,
            body,
            styles,
            content_width,
            min_height=field_min_height(title),
        ),
        Spacer(1, 0),
    ]


def _build_discussion_section(
    document: ReportDocumentV1,
    styles: dict[str, object],
    content_width: float,
) -> list[object]:
    from reportlab.platypus import Spacer

    body = _build_discussion_body(document, styles)

    return [
        build_content_field_table(
            "회의내용",
            body,
            styles,
            content_width,
            min_height=field_min_height("회의내용"),
        ),
        Spacer(1, 0),
    ]


def _build_discussion_body(
    document: ReportDocumentV1,
    styles: dict[str, object],
) -> list[object]:
    sections = sections_with_discussion(document) if document.sections else ()
    if sections:
        return _build_sectioned_discussion_body(sections, styles)
    return _build_flat_discussion_body(resolve_flat_discussion_items(document), styles)


def _build_flat_discussion_body(
    items: tuple[ReportListItem, ...],
    styles: dict[str, object],
) -> list[object]:
    from reportlab.platypus import Paragraph

    if not items:
        return [Paragraph("기록된 내용이 없습니다.", styles["empty"])]
    return [
        Paragraph(f"{index}. {escape_list_item_text(item)}", styles["item_text"])
        for index, item in enumerate(items, start=1)
    ]


def _build_sectioned_discussion_body(
    sections: tuple[ReportSection, ...],
    styles: dict[str, object],
) -> list[object]:
    body: list[object] = []
    for section_index, section in enumerate(sections, start=1):
        body.extend(_build_section_discussion_body(section_index, section, styles))
    return body


def _build_section_discussion_body(
    section_index: int,
    section: ReportSection,
    styles: dict[str, object],
) -> list[object]:
    from reportlab.platypus import Paragraph

    body: list[object] = [
        Paragraph(
            f"{section_index}. {escape_reportlab_text(section.title)}",
            styles["section_heading"],
        )
    ]
    groups = section_discussion_groups(section)
    if groups:
        for label, items in groups:
            body.append(
                Paragraph(escape_reportlab_text(label), styles["discussion_group_label"])
            )
            body.extend(_build_discussion_bullets(items, styles))
        return body

    body.extend(_build_discussion_bullets(section_discussion_items(section), styles))
    return body


def _build_discussion_bullets(
    items: tuple[ReportListItem, ...],
    styles: dict[str, object],
) -> list[object]:
    from reportlab.platypus import Paragraph

    return [
        Paragraph(f"- {escape_list_item_text(item)}", styles["discussion_bullet"])
        for item in items
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
                Paragraph(f"{index}. {render_reportlab_inline(item.task)}", styles["item_text"])
            )
    return [
        build_content_field_table(
            "향후일정",
            body,
            styles,
            content_width,
            min_height=field_min_height("향후일정"),
        ),
        Spacer(1, 0),
    ]
