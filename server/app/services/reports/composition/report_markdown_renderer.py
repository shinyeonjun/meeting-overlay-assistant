"""회의록 정본 문서를 Markdown 산출물로 렌더링한다."""

from __future__ import annotations

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


def render_report_markdown(
    *,
    session_id: str,
    document: ReportDocumentV1,
) -> str:
    """ReportDocumentV1을 기존 API가 쓰는 Markdown 회의록 형식으로 렌더링한다."""

    lines = [
        "# 회의록",
        "",
        f"- 세션 ID: {session_id}",
        "",
        "## 회의 개요",
    ]
    _append_overview(lines, document)
    _append_discussion_section(lines, document)
    _append_list_section(lines, "결정사항", resolve_decision_items(document), numbered=True)
    _append_action_section(lines, resolve_action_items(document))
    _append_list_section(
        lines,
        "특이사항",
        resolve_special_note_items(document),
        numbered=True,
    )
    return "\n".join(lines)


def _append_overview(lines: list[str], document: ReportDocumentV1) -> None:
    for label in (
        "일시",
        "장소",
        "작성자",
        "작성일",
        "참석자",
    ):
        value = _metadata_value(document.metadata, label)
        if label == "작성자" and not value:
            value = _metadata_value(document.metadata, "회의 주최자")
        if label == "작성일" and not value:
            value = _date_part(_metadata_value(document.metadata, "일시") or "")
        if value:
            lines.append(f"- {label}: {value}")
    agenda = resolve_agenda_text(document)
    if agenda:
        lines.append(f"- 안건: {agenda}")
    for item in document.summary:
        lines.append(f"- {item}")


def _append_list_section(
    lines: list[str],
    heading: str,
    items: tuple[ReportListItem, ...],
    *,
    numbered: bool = False,
) -> None:
    lines.extend(["", f"## {heading}"])
    if not items:
        lines.append("- 없음")
        return

    for index, item in enumerate(items, start=1):
        prefix = f"{index}." if numbered else "-"
        lines.append(f"{prefix} {item.text}")


def _append_discussion_section(lines: list[str], document: ReportDocumentV1) -> None:
    lines.extend(["", "## 회의내용"])
    if not document.sections:
        items = resolve_flat_discussion_items(document)
        if not items:
            lines.append("- 없음")
            return
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {item.text}")
        return

    sections = sections_with_discussion(document)
    if not sections:
        items = resolve_flat_discussion_items(document)
        if not items:
            lines.append("- 없음")
            return
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. {item.text}")
        return

    for section_index, section in enumerate(sections, start=1):
        lines.append(f"{section_index}. {section.title}")
        groups = section_discussion_groups(section)
        if groups:
            for label, items in groups:
                lines.append(f"  - {label}")
                for item in items:
                    lines.append(f"    - {item.text}")
            continue
        for item in section_discussion_items(section):
            lines.append(f"  - {item.text}")


def _append_action_section(
    lines: list[str],
    items: tuple[ReportActionItem, ...],
) -> None:
    lines.extend(["", "## 향후일정"])
    if not items:
        lines.append("- 없음")
        return

    for item in items:
        checkbox = "x" if item.status in {"완료", "해결"} else " "
        lines.append(f"- [{checkbox}] {item.task}")


def _append_text_section(
    lines: list[str],
    heading: str,
    items: tuple[str, ...],
) -> None:
    lines.extend(["", f"## {heading}"])
    if not items:
        lines.append("- 없음")
        return
    lines.extend(f"- {item}" for item in items)




def _metadata_value(fields: tuple[ReportMetaField, ...], label: str) -> str | None:
    for field in fields:
        if field.label == label:
            return field.value
    return None


def _date_part(value: str) -> str:
    parts = value.split()
    return parts[0] if parts else ""
