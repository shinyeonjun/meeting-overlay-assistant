"""회의록 정본 문서를 Markdown 산출물로 렌더링한다."""

from __future__ import annotations

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)


def render_report_markdown(
    *,
    session_id: str,
    document: ReportDocumentV1,
) -> str:
    """ReportDocumentV1을 기존 API가 쓰는 Markdown 회의록 형식으로 렌더링한다."""

    lines = [
        f"# {document.title}",
        "",
        f"- 세션 ID: {session_id}",
        "",
        "## 회의 개요",
    ]
    _append_overview(lines, document)
    _append_list_section(lines, "안건 및 논의", document.agenda, numbered=True)
    _append_list_section(lines, "질문", document.questions)
    _append_list_section(lines, "결정 사항", document.decisions, numbered=True)
    _append_action_section(lines, document.action_items)
    _append_list_section(lines, "리스크", document.risks)
    _append_text_section(lines, "참고 전사", document.transcript_excerpt)
    _append_text_section(lines, "발화자 기반 인사이트", document.speaker_insights)
    return "\n".join(lines)


def _append_overview(lines: list[str], document: ReportDocumentV1) -> None:
    for label in (
        "회의일자",
        "회의시간",
        "회의장소",
        "회의주제",
        "참석자",
        "기록 기준",
    ):
        value = _metadata_value(document.metadata, label)
        if value:
            lines.append(f"- {label}: {value}")
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
        lines.extend(_build_item_metadata_lines(item))


def _append_action_section(
    lines: list[str],
    items: tuple[ReportActionItem, ...],
) -> None:
    lines.extend(["", "## 후속 조치"])
    if not items:
        lines.append("- 없음")
        return

    for item in items:
        checkbox = "x" if item.status in {"완료", "해결"} else " "
        lines.append(f"- [{checkbox}] {item.task}")
        if item.owner and item.owner != "-":
            lines.append(f"  - 담당자: {item.owner}")
        if item.due_date and item.due_date != "-":
            lines.append(f"  - 기한: {item.due_date}")
        if item.time_range:
            lines.append(f"  - 근거 구간: {item.time_range}")
        if item.note:
            lines.append(f"  - 근거: {item.note}")


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


def _build_item_metadata_lines(item: ReportListItem) -> list[str]:
    metadata_lines: list[str] = []
    if item.speaker:
        metadata_lines.append(f"  - 발화자: {item.speaker}")
    if item.time_range:
        metadata_lines.append(f"  - 근거 구간: {item.time_range}")
    if item.evidence:
        metadata_lines.append(f"  - 근거: {item.evidence}")
    return metadata_lines


def _metadata_value(fields: tuple[ReportMetaField, ...], label: str) -> str | None:
    for field in fields:
        if field.label == label:
            return field.value
    return None
