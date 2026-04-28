"""회의록 정본 문서의 렌더링용 파생 데이터를 계산한다."""

from __future__ import annotations

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportSection,
)

DISCUSSION_GROUP_LABELS = (
    ("논의 배경", "background"),
    ("주요 의견", "opinions"),
    ("검토 내용", "review"),
    ("정리된 방향", "direction"),
)


def sections_with_discussion(document: ReportDocumentV1) -> tuple[ReportSection, ...]:
    """논의 내용이 있는 회의내용 섹션만 반환한다."""

    return tuple(
        section
        for section in document.sections
        if section_discussion_groups(section) or section_discussion_items(section)
    )


def section_discussion_groups(
    section: ReportSection,
) -> tuple[tuple[str, tuple[ReportListItem, ...]], ...]:
    """구조화된 회의내용 그룹을 반환한다."""

    groups: list[tuple[str, tuple[ReportListItem, ...]]] = []
    for label, attr_name in DISCUSSION_GROUP_LABELS:
        items = tuple(getattr(section, attr_name))
        if items:
            groups.append((label, items))
    return tuple(groups)


def section_discussion_items(section: ReportSection) -> tuple[ReportListItem, ...]:
    """기존 평면 회의내용 항목을 반환한다."""

    return section.discussion


def resolve_flat_discussion_items(
    document: ReportDocumentV1,
) -> tuple[ReportListItem, ...]:
    """계층형 섹션이 없을 때 쓸 평면 논의 목록을 만든다."""

    if document.discussion:
        return document.discussion
    return ()


def resolve_decision_items(document: ReportDocumentV1) -> tuple[ReportListItem, ...]:
    """문서 전체 결정사항을 반환하고, 없으면 섹션 하위 결정사항을 평면화한다."""

    if document.decisions:
        return document.decisions
    return tuple(
        item
        for section in document.sections
        for item in section.decisions
    )


def resolve_agenda_text(document: ReportDocumentV1) -> str:
    """회의개요의 안건 칸에 들어갈 주제 문자열을 만든다."""

    agenda_items = tuple(item.text.strip() for item in document.agenda if item.text.strip())
    if agenda_items:
        return " / ".join(agenda_items)
    section_titles = tuple(
        section.title.strip() for section in document.sections if section.title.strip()
    )
    if section_titles:
        return " / ".join(section_titles)
    return document.title.strip()


def resolve_special_note_items(document: ReportDocumentV1) -> tuple[ReportListItem, ...]:
    """문서 전체 특이사항을 반환하고, 없으면 섹션 하위 특이사항을 평면화한다."""

    if document.risks:
        return document.risks
    return tuple(
        item
        for section in document.sections
        for item in section.special_notes
    )


def resolve_action_items(document: ReportDocumentV1) -> tuple[ReportActionItem, ...]:
    """문서 전체 향후일정을 반환하고, 없으면 섹션 하위 향후일정을 평면화한다."""

    if document.action_items:
        return document.action_items
    return tuple(
        item
        for section in document.sections
        for item in section.action_items
    )
