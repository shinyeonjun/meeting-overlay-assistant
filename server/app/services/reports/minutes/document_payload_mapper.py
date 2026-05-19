"""회의록 AI 분석 payload를 ReportDocumentV1로 변환한다."""

from __future__ import annotations

from dataclasses import dataclass, replace

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportSection,
)
from server.app.services.reports.minutes.normalization import (
    clean_text,
    limit_text,
    normalize_optional,
    normalize_owner,
    normalize_status,
)
from server.app.services.reports.minutes.payload_items import (
    coerce_text_item_payload,
    extract_string_items,
    extract_text_item_payloads,
    iter_raw_list,
)


@dataclass(frozen=True)
class _AnalyzedSection:
    title: str
    time_range: str | None
    background: tuple[ReportListItem, ...]
    opinions: tuple[ReportListItem, ...]
    review: tuple[ReportListItem, ...]
    direction: tuple[ReportListItem, ...]


def build_report_document_from_minutes_payload(
    payload: dict[str, object],
    *,
    fallback_document: ReportDocumentV1,
) -> ReportDocumentV1 | None:
    """AI payload가 실질 내용을 담고 있으면 fallback 문서에 반영한다."""

    overview = _parse_overview(payload.get("overview"))
    agenda = _parse_agenda(payload.get("agenda"))
    sections = _parse_sections(payload.get("sections"))
    report_sections = _build_report_sections(sections)
    discussion = _build_discussion_from_sections(sections)
    decisions = _parse_list_items(
        payload.get("decisions"),
        include_important_phrases=False,
    )
    special_notes = _parse_list_items(
        payload.get("special_notes"),
        include_important_phrases=False,
    )
    follow_up = _parse_action_items(payload.get("follow_up"))

    if not any((overview, agenda, discussion, decisions, special_notes, follow_up)):
        return None

    return replace(
        fallback_document,
        summary=tuple(overview) or fallback_document.summary,
        sections=tuple(report_sections),
        agenda=tuple(agenda) or fallback_document.agenda,
        discussion=tuple(discussion),
        decisions=tuple(decisions) or fallback_document.decisions,
        risks=tuple(special_notes) or fallback_document.risks,
        action_items=tuple(follow_up) or fallback_document.action_items,
    )


def _parse_list_items(
    value: object,
    *,
    include_important_phrases: bool = True,
) -> list[ReportListItem]:
    if not isinstance(value, list):
        return []
    items: list[ReportListItem] = []
    for raw_item in value:
        item = coerce_text_item_payload(raw_item)
        if item is None:
            continue
        items.append(
            _report_list_item_from_payload(
                item,
                evidence=(
                    limit_text(clean_text(raw_item.get("evidence")), 180)
                    if isinstance(raw_item, dict)
                    else ""
                ),
                time_range=(
                    normalize_optional(raw_item.get("time_range"))
                    if isinstance(raw_item, dict)
                    else None
                ),
                include_important_phrases=include_important_phrases,
            )
        )
    return items


def _report_list_item_from_payload(
    payload: dict[str, object],
    *,
    evidence: str = "",
    time_range: str | None = None,
    include_important_phrases: bool = True,
) -> ReportListItem:
    phrases = payload.get("important_phrases")
    return ReportListItem(
        text=clean_text(payload.get("text")),
        evidence=evidence,
        time_range=time_range,
        important_phrases=(
            tuple(str(phrase) for phrase in phrases)
            if include_important_phrases and isinstance(phrases, list)
            else ()
        ),
    )


def _parse_overview(value: object) -> list[str]:
    overview: list[str] = []
    for raw_item in extract_string_items(value):
        text = clean_text(raw_item)
        if text:
            overview.append(limit_text(text, 220) or "")
    return overview


def _parse_agenda(value: object) -> list[ReportListItem]:
    text = next(iter(extract_string_items(value)), "")
    if not text:
        return []
    return [ReportListItem(text=text)]


def _parse_section_text_items(value: object) -> tuple[ReportListItem, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        _report_list_item_from_payload(item)
        for item in extract_text_item_payloads(value)
    )


def _parse_sections(value: object) -> list[_AnalyzedSection]:
    if not isinstance(value, list):
        return []
    sections: list[_AnalyzedSection] = []
    for raw_section in value:
        if not isinstance(raw_section, dict):
            continue
        title = clean_text(raw_section.get("title"))
        if not title:
            continue
        sections.append(
            _AnalyzedSection(
                title=limit_text(title, 120) or title,
                time_range=normalize_optional(raw_section.get("time_range")),
                background=_parse_section_text_items(raw_section.get("background")),
                opinions=_parse_section_text_items(raw_section.get("opinions")),
                review=_parse_section_text_items(raw_section.get("review")),
                direction=_parse_section_text_items(raw_section.get("direction")),
            )
        )
    return sections


def _build_report_sections(
    sections: list[_AnalyzedSection],
) -> list[ReportSection]:
    return [
        ReportSection(
            title=section.title,
            time_range=section.time_range,
            background=section.background,
            opinions=section.opinions,
            review=section.review,
            direction=section.direction,
        )
        for section in sections
    ]


def _build_discussion_from_sections(
    sections: list[_AnalyzedSection],
) -> list[ReportListItem]:
    discussion: list[ReportListItem] = []
    for section in sections:
        discussion.extend(section.background)
        discussion.extend(section.opinions)
        discussion.extend(section.review)
        discussion.extend(section.direction)
    return discussion


def _parse_action_items(value: object) -> list[ReportActionItem]:
    items: list[ReportActionItem] = []
    for raw_item in iter_raw_list(value):
        if not isinstance(raw_item, dict):
            continue
        task = clean_text(raw_item.get("task"))
        if not task:
            continue
        items.append(
            ReportActionItem(
                task=limit_text(task, 180),
                owner=normalize_owner(raw_item.get("owner")) or "",
                due_date=normalize_optional(raw_item.get("due_date")) or "",
                status=normalize_status(raw_item.get("status")) or "",
                note=limit_text(clean_text(raw_item.get("note")), 180),
            )
        )
    return items
