"""이벤트 영역의 event lifecycle service 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import replace
from time import time

from server.app.domain.events import MeetingEvent, validate_event_transition
from server.app.domain.shared.enums import EventState
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)


def _now_ms() -> int:
    return int(time() * 1000)


class EventLifecycleService:
    """이벤트 상태 전이와 벌크 전이를 담당한다."""

    def __init__(self, event_repository: MeetingEventRepository) -> None:
        self._event_repository = event_repository

    def transition_event(
        self,
        session_id: str,
        event_id: str,
        *,
        target_state: EventState,
        title: str | None = None,
        body: str | None = None,
        evidence_text: str | None = None,
        speaker_label: str | None = None,
    ) -> MeetingEvent:
        """단건 이벤트를 검증된 상태로 전이한다."""

        existing = self._get_event(session_id, event_id)
        validate_event_transition(existing.event_type, existing.state, target_state)

        updated = replace(
            existing,
            state=target_state,
            title=title if title is not None else existing.title,
            body=body if body is not None else existing.body,
            evidence_text=evidence_text if evidence_text is not None else existing.evidence_text,
            speaker_label=speaker_label if speaker_label is not None else existing.speaker_label,
            updated_at_ms=_now_ms(),
        )
        return self._event_repository.update(updated)

    def bulk_transition_events(
        self,
        session_id: str,
        event_ids: list[str],
        *,
        target_state: EventState,
    ) -> list[MeetingEvent]:
        """여러 이벤트를 같은 상태로 한 번에 전이한다."""

        return [
            self.transition_event(
                session_id,
                event_id,
                target_state=target_state,
            )
            for event_id in event_ids
        ]

    def _get_event(self, session_id: str, event_id: str) -> MeetingEvent:
        event = self._event_repository.get_by_id(event_id)
        if event is None or event.session_id != session_id:
            raise ValueError("이벤트를 찾을 수 없습니다.")
        return event
