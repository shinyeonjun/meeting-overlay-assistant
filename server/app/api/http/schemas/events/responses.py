"""이벤트 응답 스키마."""

from __future__ import annotations

from pydantic import BaseModel


class EventItemResponse(BaseModel):
    """이벤트 단건 응답."""

    id: str
    session_id: str
    event_type: str
    title: str
    body: str | None
    evidence_text: str | None
    speaker_label: str | None
    state: str
    source_utterance_id: str | None
    event_source: str = "live"
    created_at_ms: int
    updated_at_ms: int
    finalized_at_ms: int | None = None


class EventListResponse(BaseModel):
    """이벤트 목록 응답."""

    items: list[EventItemResponse]


class BulkEventTransitionResponse(BaseModel):
    """벌크 상태 전이 응답."""

    updated_count: int
    target_state: str
    items: list[EventItemResponse]
