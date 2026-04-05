"""이벤트 라우트 공통 지원 함수."""

from __future__ import annotations

from fastapi import HTTPException

from server.app.api.http.schemas.events.responses import EventItemResponse
from server.app.domain.events import MeetingEvent


def to_event_response(event: MeetingEvent) -> EventItemResponse:
    """도메인 이벤트를 API 응답으로 변환한다."""

    return EventItemResponse(
        id=event.id,
        session_id=event.session_id,
        event_type=event.event_type.value,
        title=event.title,
        body=event.body,
        evidence_text=event.evidence_text,
        speaker_label=event.speaker_label,
        state=event.state.value,
        source_utterance_id=event.source_utterance_id,
        event_source=event.event_source,
        created_at_ms=event.created_at_ms,
        updated_at_ms=event.updated_at_ms,
        finalized_at_ms=event.finalized_at_ms,
    )


def raise_event_error(error: ValueError) -> None:
    """이벤트 서비스 예외를 적절한 HTTP 예외로 변환한다."""

    detail = str(error)
    status_code = 404 if detail == "이벤트를 찾을 수 없습니다." else 400
    raise HTTPException(status_code=status_code, detail=detail) from error
