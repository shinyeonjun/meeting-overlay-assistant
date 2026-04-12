"""이벤트 영역의 event management service 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import replace
from time import time

from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)


def _now_ms() -> int:
    return int(time() * 1000)


class EventManagementService:
    """사용자 기준 이벤트 조회, 수정, 삭제를 담당한다."""

    def __init__(self, event_repository: MeetingEventRepository) -> None:
        self._event_repository = event_repository

    def list_events(
        self,
        session_id: str,
        *,
        event_type: EventType | None = None,
        state: EventState | None = None,
    ) -> list[MeetingEvent]:
        """세션 이벤트를 조회하고 필요하면 타입과 상태로 필터링한다."""

        events = self._event_repository.list_by_session(session_id)
        if event_type is not None:
            events = [event for event in events if event.event_type == event_type]
        if state is not None:
            events = [event for event in events if event.state == state]
        return events

    def get_event(self, session_id: str, event_id: str) -> MeetingEvent:
        """세션 범위 안의 이벤트 단건을 조회한다."""

        event = self._event_repository.get_by_id(event_id)
        if event is None or event.session_id != session_id:
            raise ValueError("이벤트를 찾을 수 없습니다.")
        return event

    def update_event(
        self,
        session_id: str,
        event_id: str,
        *,
        event_type: EventType | None = None,
        title: str | None = None,
        body: str | None = None,
        evidence_text: str | None = None,
        speaker_label: str | None = None,
    ) -> MeetingEvent:
        """이벤트의 최소 편집 필드만 수정한다."""

        existing = self.get_event(session_id, event_id)
        updated = replace(
            existing,
            event_type=event_type or existing.event_type,
            title=title if title is not None else existing.title,
            body=body if body is not None else existing.body,
            evidence_text=evidence_text if evidence_text is not None else existing.evidence_text,
            speaker_label=speaker_label if speaker_label is not None else existing.speaker_label,
            updated_at_ms=_now_ms(),
        )
        return self._event_repository.update(updated)

    def delete_event(self, session_id: str, event_id: str) -> None:
        """세션 범위 안의 이벤트를 삭제한다."""

        _ = self.get_event(session_id, event_id)
        self._event_repository.delete(event_id)
