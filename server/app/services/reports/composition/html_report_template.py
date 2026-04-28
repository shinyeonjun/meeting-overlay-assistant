"""HTML/CSS 기반 회의록 템플릿 렌더러."""

from __future__ import annotations

from html import escape
from pathlib import Path
from string import Template

from server.app.services.reports.composition.report_document import (
    REPORT_DOCUMENT_VERSION,
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    ReportSection,
    report_document_to_dict,
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


def build_sample_report_document() -> ReportDocumentV1:
    """디자인 확인용 샘플 문서를 만든다."""

    return ReportDocumentV1(
        title="CAPS 회의록 품질 개선 회의",
        metadata=(
            ReportMetaField("회의제목", "고객중심과 외부지향 회사전략 인식 제고 회의"),
            ReportMetaField("일시", "2026-04-25 10:00 - 10:45"),
            ReportMetaField("장소", "본사 4층 회의실"),
            ReportMetaField("작성자", "기획팀 박민수 대리"),
            ReportMetaField("작성일", "2026-04-25"),
            ReportMetaField("참석자", "기획팀 박민수 과장, 이지현 대리 / 개발팀 김성준 대리"),
        ),
        summary=(
            "고객중심과 외부지향 회사전략에 대한 구성원 인식을 높이기 위한 회의록이다.",
        ),
        sections=(
            ReportSection(
                title="현재 회사전략에 대한 사원들의 이해도 점검",
                background=(
                    ReportListItem(
                        "고객중심과 외부지향 회사전략에 대한 구성원 이해도를 확인할 필요가 있었다.",
                    ),
                ),
                opinions=(
                    ReportListItem(
                        "고객중심은 고객의 입장에서 고객이 좋아할 만한 서비스를 제공하는 방향으로 이해한다.",
                    ),
                    ReportListItem(
                        "외부지향은 살아있는 서비스를 외부에 잘 알리는 활동으로 정리한다.",
                    ),
                ),
                review=(
                    ReportListItem(
                        "회사전략이 현장 업무에서 구체적으로 인식되고 있는지 점검했다.",
                    ),
                ),
                direction=(
                    ReportListItem(
                        "회사전략을 구성원이 이해할 수 있도록 인식 제고 방안을 마련한다.",
                    ),
                ),
            ),
            ReportSection(
                title="인식 제고를 위한 개선방안",
                background=(
                    ReportListItem(
                        "회사전략을 개인 업무에서 실천할 수 있는 방안이 필요하다는 점을 확인했다.",
                    ),
                ),
                opinions=(
                    ReportListItem(
                        "회사 전략을 바탕으로 개인이 실천할 수 있는 작은 업무부터 실행한다.",
                    ),
                ),
                review=(
                    ReportListItem(
                        "구성원이 회사전략을 인지할 수 있도록 구체적인 실행방안을 마련한다.",
                    ),
                ),
                direction=(
                    ReportListItem(
                        "사원 의견을 취합한 뒤 다음 회의에서 개선방안을 구체화한다.",
                    ),
                ),
            ),
        ),
        agenda=(ReportListItem("고객중심과 외부지향 회사전략에 대한 인식제고"),),
        decisions=(
            ReportListItem(
                "회사전략에 대한 사원들의 의견을 취합 및 수렴한다.",
            ),
            ReportListItem(
                "다음 주 목요일 개선방안에 대한 구체적 절차를 의논한다.",
            ),
        ),
        action_items=(
            ReportActionItem(
                task="10/4(목) 10:00시 4층 회의실에서 후속 회의를 진행한다.",
            ),
        ),
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


def _render_numbered_section(
    title: str,
    items: tuple[str, ...],
    *,
    compact: bool = False,
) -> str:
    section_class = "report-section compact" if compact else "report-section"
    if not items:
        item_html = '<p class="empty-state">기록된 내용이 없습니다.</p>'
    else:
        item_html = "\n".join(
            [
                '<ol class="numbered-list">',
                *[f"<li>{_escape_multiline(item)}</li>" for item in items],
                "</ol>",
            ]
        )
    return "\n".join(
        [
            f'<section class="{section_class}">',
            f'<h2 class="section-title">{_escape_text(title)}</h2>',
            item_html,
            "</section>",
        ]
    )


def _render_list_item_section(title: str, items: tuple[ReportListItem, ...]) -> str:
    if not items:
        item_html = '<p class="empty-state">기록된 내용이 없습니다.</p>'
    else:
        rendered_items = []
        for item in items:
            rendered_items.append(
                "<li>"
                f'<span class="item-text">{_escape_multiline(item.text)}</span>'
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
                    f'<span class="item-text">{section_index}. {_escape_text(section.title)}</span>',
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
            f'<span class="item-text">{_escape_multiline(item.text)}</span>'
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
                f'<span class="item-text">{_escape_multiline(item.task)}</span>'
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


def _escape_multiline(value: str) -> str:
    return _escape_text(value).replace("\n", "<br>")
