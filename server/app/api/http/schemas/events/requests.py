"""HTTP 계층에서 이벤트 관련 requests 구성을 담당한다."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EventUpdateRequest(BaseModel):
    """이벤트 수정 요청."""

    event_type: str | None = None
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    state: str | None = None
    evidence_text: str | None = None
    speaker_label: str | None = None


class EventTransitionRequest(BaseModel):
    """단건 이벤트 상태 전이 요청."""

    target_state: str
    title: str | None = Field(default=None, min_length=1)
    body: str | None = None
    evidence_text: str | None = None
    speaker_label: str | None = None


class BulkEventTransitionRequest(BaseModel):
    """여러 이벤트 상태 전이 요청."""

    event_ids: list[str] = Field(min_length=1)
    target_state: str
