"""이벤트 관리 API 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
    priority: int
    assignee: str | None
    due_date: str | None
    topic_group: str | None
    source_utterance_id: str | None
    source_screen_id: str | None
    created_at_ms: int
    updated_at_ms: int
    input_source: str | None
    insight_scope: str


class EventListResponse(BaseModel):
    """이벤트 목록 응답."""

    items: list[EventItemResponse]


class EventUpdateRequest(BaseModel):
    """이벤트 수정 요청."""

    event_type: str | None = None
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    state: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    evidence_text: str | None = None
    speaker_label: str | None = None
    topic_group: str | None = None
    priority: int | None = None


class EventTransitionRequest(BaseModel):
    """단건 이벤트 상태 전이 요청."""

    target_state: str
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    evidence_text: str | None = None
    speaker_label: str | None = None
    topic_group: str | None = None


class BulkEventTransitionRequest(BaseModel):
    """여러 이벤트 상태를 한 번에 바꾸는 요청."""

    event_ids: list[str] = Field(min_length=1)
    target_state: str
    assignee: str | None = None
    due_date: str | None = None


class BulkEventTransitionResponse(BaseModel):
    """벌크 상태 전이 응답."""

    updated_count: int
    target_state: str
    items: list[EventItemResponse]
