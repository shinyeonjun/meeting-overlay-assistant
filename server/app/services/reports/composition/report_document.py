"""회의록 HTML/PDF/Markdown 렌더러가 공유하는 정본 문서 모델."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


REPORT_DOCUMENT_VERSION = "report_v1"


@dataclass(frozen=True)
class ReportMetaField:
    """회의록 상단 메타데이터 항목."""

    label: str
    value: str


@dataclass(frozen=True)
class ReportListItem:
    """회의록 목록형 섹션 항목."""

    text: str
    speaker: str | None = None
    evidence: str | None = None
    time_range: str | None = None


@dataclass(frozen=True)
class ReportActionItem:
    """회의록 액션 아이템 표 항목."""

    task: str
    owner: str = ""
    due_date: str = ""
    status: str = ""
    note: str | None = None
    time_range: str | None = None


@dataclass(frozen=True)
class ReportSection:
    """회의록의 안건 단위 섹션."""

    title: str
    time_range: str | None = None
    evidence: str | None = None
    background: tuple[ReportListItem, ...] = field(default_factory=tuple)
    opinions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    review: tuple[ReportListItem, ...] = field(default_factory=tuple)
    direction: tuple[ReportListItem, ...] = field(default_factory=tuple)
    discussion: tuple[ReportListItem, ...] = field(default_factory=tuple)
    decisions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    action_items: tuple[ReportActionItem, ...] = field(default_factory=tuple)
    special_notes: tuple[ReportListItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReportDocumentV1:
    """회의록 생성 파이프라인의 정본 구조."""

    title: str = "회의록"
    metadata: tuple[ReportMetaField, ...] = field(default_factory=tuple)
    summary: tuple[str, ...] = field(default_factory=tuple)
    sections: tuple[ReportSection, ...] = field(default_factory=tuple)
    agenda: tuple[ReportListItem, ...] = field(default_factory=tuple)
    discussion: tuple[ReportListItem, ...] = field(default_factory=tuple)
    decisions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    action_items: tuple[ReportActionItem, ...] = field(default_factory=tuple)
    questions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    risks: tuple[ReportListItem, ...] = field(default_factory=tuple)
    transcript_excerpt: tuple[str, ...] = field(default_factory=tuple)
    speaker_insights: tuple[str, ...] = field(default_factory=tuple)


def report_document_to_dict(document: ReportDocumentV1) -> dict[str, object]:
    """회의록 정본 문서를 artifact로 저장할 수 있는 dict로 변환한다."""

    return {
        "template_version": REPORT_DOCUMENT_VERSION,
        "document": asdict(document),
    }


def report_document_from_dict(payload: dict[str, Any]) -> ReportDocumentV1:
    """artifact나 편집 요청 payload에서 정본 문서를 복원한다."""

    document_payload = payload.get("document") if "document" in payload else payload
    if not isinstance(document_payload, dict):
        raise ValueError("회의록 문서 payload가 올바르지 않습니다.")

    return ReportDocumentV1(
        title=_string_value(document_payload.get("title"), "회의록"),
        metadata=tuple(
            _meta_field_from_dict(item) for item in _list_value(document_payload.get("metadata"))
        ),
        summary=tuple(_string_value(item) for item in _list_value(document_payload.get("summary"))),
        sections=tuple(
            _section_from_dict(item) for item in _list_value(document_payload.get("sections"))
        ),
        agenda=tuple(
            _list_item_from_dict(item) for item in _list_value(document_payload.get("agenda"))
        ),
        discussion=tuple(
            _list_item_from_dict(item) for item in _list_value(document_payload.get("discussion"))
        ),
        decisions=tuple(
            _list_item_from_dict(item) for item in _list_value(document_payload.get("decisions"))
        ),
        action_items=tuple(
            _action_item_from_dict(item) for item in _list_value(document_payload.get("action_items"))
        ),
        questions=tuple(
            _list_item_from_dict(item) for item in _list_value(document_payload.get("questions"))
        ),
        risks=tuple(
            _list_item_from_dict(item) for item in _list_value(document_payload.get("risks"))
        ),
        transcript_excerpt=tuple(
            _string_value(item) for item in _list_value(document_payload.get("transcript_excerpt"))
        ),
        speaker_insights=tuple(
            _string_value(item) for item in _list_value(document_payload.get("speaker_insights"))
        ),
    )


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list | tuple):
        return list(value)
    return []


def _optional_string_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_value(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _meta_field_from_dict(value: Any) -> ReportMetaField:
    if isinstance(value, dict):
        return ReportMetaField(
            label=_string_value(value.get("label")),
            value=_string_value(value.get("value")),
        )
    return ReportMetaField(label="", value=_string_value(value))


def _list_item_from_dict(value: Any) -> ReportListItem:
    if isinstance(value, dict):
        return ReportListItem(
            text=_string_value(value.get("text")),
            speaker=_optional_string_value(value.get("speaker")),
            evidence=_optional_string_value(value.get("evidence")),
            time_range=_optional_string_value(value.get("time_range")),
        )
    return ReportListItem(text=_string_value(value))


def _action_item_from_dict(value: Any) -> ReportActionItem:
    if isinstance(value, dict):
        return ReportActionItem(
            task=_string_value(value.get("task")),
            owner=_string_value(value.get("owner")),
            due_date=_string_value(value.get("due_date")),
            status=_string_value(value.get("status")),
            note=_optional_string_value(value.get("note")),
            time_range=_optional_string_value(value.get("time_range")),
        )
    return ReportActionItem(task=_string_value(value))


def _section_from_dict(value: Any) -> ReportSection:
    if not isinstance(value, dict):
        return ReportSection(title=_string_value(value))
    return ReportSection(
        title=_string_value(value.get("title"), "회의내용"),
        time_range=_optional_string_value(value.get("time_range")),
        evidence=_optional_string_value(value.get("evidence")),
        background=tuple(_list_item_from_dict(item) for item in _list_value(value.get("background"))),
        opinions=tuple(_list_item_from_dict(item) for item in _list_value(value.get("opinions"))),
        review=tuple(_list_item_from_dict(item) for item in _list_value(value.get("review"))),
        direction=tuple(_list_item_from_dict(item) for item in _list_value(value.get("direction"))),
        discussion=tuple(_list_item_from_dict(item) for item in _list_value(value.get("discussion"))),
        decisions=tuple(_list_item_from_dict(item) for item in _list_value(value.get("decisions"))),
        action_items=tuple(
            _action_item_from_dict(item) for item in _list_value(value.get("action_items"))
        ),
        special_notes=tuple(
            _list_item_from_dict(item) for item in _list_value(value.get("special_notes"))
        ),
    )
