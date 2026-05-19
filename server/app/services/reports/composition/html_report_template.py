"""HTML/CSS 기반 회의록 템플릿 렌더러."""

from __future__ import annotations

from html import escape
from pathlib import Path
from string import Template

from server.app.services.reports.composition.inline_formatting import render_html_inline
from server.app.services.reports.composition.report_document import (
    REPORT_DOCUMENT_VERSION,
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
from server.app.services.reports.composition.sample_report_document import (
    build_sample_report_document,
)

TEMPLATE_VERSION = REPORT_DOCUMENT_VERSION
_TEMPLATE_DIR = Path(__file__).with_name("templates") / TEMPLATE_VERSION


def render_report_html(document: ReportDocumentV1) -> str:
    """회의록 문서를 HTML 문자열로 렌더링한다."""

    template = Template((_TEMPLATE_DIR / "template.html").read_text(encoding="utf-8"))
    stylesheet = (_TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    body = "\n".join(
        [
            '<main class="report-page">',
            _render_cover_header(document),
            _render_overview_section(document),
            _render_minutes_content_section(document),
            "</main>",
        ]
    )
    return template.substitute(
        document_title=_escape_text(document.title),
        stylesheet=stylesheet,
        body=body,
    )


def render_sample_report_html() -> str:
    """디자인 확인용 샘플 HTML을 렌더링한다."""

    return render_report_html(build_sample_report_document())


def _render_cover_header(document: ReportDocumentV1) -> str:
    return "\n".join(
        [
            '<header class="report-header">',
            "<h1>회의록</h1>",
            "</header>",
        ]
    )


def _render_overview_section(document: ReportDocumentV1) -> str:
    return "\n".join(
        [
            '<section class="overview-section">',
            '<h2 class="minutes-section-title">1. 회의개요</h2>',
            _render_metadata_table(document),
            "</section>",
        ]
    )


def _render_metadata_table(document: ReportDocumentV1) -> str:
    fields = document.metadata
    meeting_title = (
        _metadata_value(fields, "회의제목")
        or (document.title if document.title.strip() and document.title.strip() != "회의록" else "")
    )
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
        f'<tr><th>회의제목</th><td colspan="3">{_escape_text(meeting_title)}</td></tr>',
        (
            "<tr>"
            f"<th>일시</th><td>{_escape_text(meeting_datetime)}</td>"
            f"<th>장소</th><td>{_escape_text(location)}</td>"
            "</tr>"
        ),
        (
            "<tr>"
            f"<th>작성자</th><td>{_escape_text(writer)}</td>"
            f"<th>작성일</th><td>{_escape_text(written_date)}</td>"
            "</tr>"
        ),
        f'<tr><th>참석자</th><td colspan="3">{_escape_text(participants)}</td></tr>',
        f'<tr><th>안건</th><td colspan="3">{_escape_text(agenda)}</td></tr>',
    ]

    return "\n".join(
        [
            '<section class="metadata-section">',
            '<table class="metadata-table">',
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</section>",
        ]
    )


def _date_part(value: str) -> str:
    parts = value.split()
    return parts[0] if parts else ""


def _metadata_value(fields: tuple[ReportMetaField, ...], label: str) -> str | None:
    for field in fields:
        if field.label == label:
            return field.value
    return None


def _render_list_item_section(title: str, items: tuple[ReportListItem, ...]) -> str:
    if not items:
        item_html = '<p class="empty-state">기록된 내용이 없습니다.</p>'
    else:
        rendered_items = []
        for item in items:
            rendered_items.append(
                "<li>"
                f'<span class="item-text">{_render_list_item_text(item)}</span>'
                "</li>"
            )
        item_html = "\n".join(['<ol class="numbered-list">', *rendered_items, "</ol>"])

    return "\n".join(
        [
            f'<section class="content-field-section {_field_class_name(title)}">',
            f'<div class="content-field-label">{_escape_text(title)}</div>',
            f'<div class="content-field-body">{item_html}</div>',
            "</section>",
        ]
    )


def _render_discussion_section(document: ReportDocumentV1) -> str:
    if not document.sections:
        return _render_list_item_section(
            "회의내용",
            resolve_flat_discussion_items(document),
        )

    sections = sections_with_discussion(document)
    if not sections:
        return _render_list_item_section(
            "회의내용",
            resolve_flat_discussion_items(document),
        )

    rendered_sections = []
    for section_index, section in enumerate(sections, start=1):
        groups = section_discussion_groups(section)
        discussion_body = (
            _render_discussion_groups(groups)
            if groups
            else _render_discussion_points(section_discussion_items(section))
        )
        rendered_sections.append(
            "\n".join(
                [
                    '<li class="discussion-section">',
                    '<div class="discussion-section-heading">',
                    f'<span class="discussion-section-number">{section_index}.</span>',
                    f'<strong class="discussion-section-title">{_escape_text(section.title)}</strong>',
                    "</div>",
                    discussion_body,
                    "</li>",
                ]
            )
        )

    item_html = "\n".join(
        ['<ol class="numbered-list discussion-section-list">', *rendered_sections, "</ol>"]
    )
    return "\n".join(
        [
            '<section class="content-field-section field-discussion">',
            '<div class="content-field-label">회의내용</div>',
            f'<div class="content-field-body">{item_html}</div>',
            "</section>",
        ]
    )


def _render_discussion_groups(
    groups: tuple[tuple[str, tuple[ReportListItem, ...]], ...],
) -> str:
    rendered_groups = []
    for label, items in groups:
        rendered_groups.append(
            "\n".join(
                [
                    '<div class="discussion-group">',
                    f'<p class="discussion-group-label">{_escape_text(label)}</p>',
                    _render_discussion_points(items),
                    "</div>",
                ]
            )
        )
    return "\n".join(rendered_groups)


def _render_discussion_points(items: tuple[ReportListItem, ...]) -> str:
    rendered_items = []
    for item in items:
        rendered_items.append(
            "<li>"
            f'<span class="item-text">{_render_list_item_text(item)}</span>'
            "</li>"
        )
    return "\n".join(['<ul class="discussion-point-list">', *rendered_items, "</ul>"])


def _render_action_section(items: tuple[ReportActionItem, ...]) -> str:
    if not items:
        item_html = '<p class="empty-state">기록된 향후일정이 없습니다.</p>'
    else:
        rendered_items = []
        for item in items:
            rendered_items.append(
                "<li>"
                f'<span class="item-text">{render_html_inline(item.task)}</span>'
                "</li>"
            )
        item_html = "\n".join(['<ol class="numbered-list">', *rendered_items, "</ol>"])

    return "\n".join(
        [
            '<section class="content-field-section field-schedule">',
            '<div class="content-field-label">향후일정</div>',
            f'<div class="content-field-body">{item_html}</div>',
            "</section>",
        ]
    )


def _render_minutes_content_section(document: ReportDocumentV1) -> str:
    return "\n".join(
        [
            '<section class="minutes-content-section">',
            '<h2 class="minutes-section-title">2. 회의내용</h2>',
            _render_discussion_section(document),
            _render_list_item_section("결정사항", resolve_decision_items(document)),
            _render_action_section(resolve_action_items(document)),
            _render_list_item_section("특이사항", resolve_special_note_items(document)),
            "</section>",
        ]
    )


def _field_class_name(title: str) -> str:
    class_by_title = {
        "안건": "field-agenda",
        "논의 내용": "field-discussion",
        "회의내용": "field-discussion",
        "결정사항": "field-decisions",
        "특이 사항": "field-special",
        "특이사항": "field-special",
        "추후 일정": "field-schedule",
        "향후일정": "field-schedule",
    }
    return class_by_title.get(title, "field-generic")


def _escape_text(value: str) -> str:
    return escape(value, quote=True)


def _render_list_item_text(item: ReportListItem) -> str:
    return render_html_inline(item.text, item.important_phrases)
