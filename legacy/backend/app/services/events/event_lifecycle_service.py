"""이벤트 상태 전이와 벌크 전이를 담당한다."""

from __future__ import annotations

from dataclasses import replace
from time import time

from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.shared.enums import EventState, EventType
from backend.app.repositories.contracts.meeting_event_repository import (
    MeetingEventRepository,
)


def _now_ms() -> int:
    return int(time() * 1000)


class EventLifecycleService:
    """이벤트 타입별 허용 상태 전이를 검증하고 반영한다."""

    _ALLOWED_TRANSITIONS: dict[EventType, dict[EventState, set[EventState]]] = {
        EventType.QUESTION: {
            EventState.OPEN: {EventState.ANSWERED, EventState.UNRESOLVED, EventState.CLOSED},
            EventState.ANSWERED: {EventState.CLOSED},
            EventState.UNRESOLVED: {EventState.CLOSED},
        },
        EventType.DECISION: {
            EventState.CANDIDATE: {EventState.CONFIRMED, EventState.UPDATED, EventState.CLOSED},
            EventState.OPEN: {EventState.CONFIRMED, EventState.UPDATED, EventState.CLOSED},
            EventState.CONFIRMED: {EventState.UPDATED, EventState.CLOSED},
            EventState.UPDATED: {EventState.CONFIRMED, EventState.CLOSED},
        },
        EventType.ACTION_ITEM: {
            EventState.CANDIDATE: {EventState.CONFIRMED, EventState.UPDATED, EventState.CLOSED},
            EventState.OPEN: {EventState.CONFIRMED, EventState.UPDATED, EventState.CLOSED},
            EventState.CONFIRMED: {EventState.UPDATED, EventState.CLOSED},
            EventState.UPDATED: {EventState.CONFIRMED, EventState.CLOSED},
        },
        EventType.RISK: {
            EventState.OPEN: {EventState.ACTIVE, EventState.MONITORING, EventState.RESOLVED, EventState.CLOSED},
            EventState.ACTIVE: {EventState.MONITORING, EventState.RESOLVED, EventState.CLOSED},
            EventState.MONITORING: {EventState.RESOLVED, EventState.CLOSED},
            EventState.RESOLVED: {EventState.CLOSED},
        },
    }

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
        assignee: str | None = None,
        due_date: str | None = None,
        evidence_text: str | None = None,
        speaker_label: str | None = None,
        topic_group: str | None = None,
    ) -> MeetingEvent:
        """단건 이벤트를 검증된 상태로 전이한다."""

        existing = self._get_event(session_id, event_id)
        self._validate_transition(existing, target_state)

        updated = replace(
            existing,
            state=target_state,
            title=title if title is not None else existing.title,
            body=body if body is not None else existing.body,
            assignee=assignee if assignee is not None else existing.assignee,
            due_date=due_date if due_date is not None else existing.due_date,
            evidence_text=evidence_text if evidence_text is not None else existing.evidence_text,
            speaker_label=speaker_label if speaker_label is not None else existing.speaker_label,
            topic_group=topic_group if topic_group is not None else existing.topic_group,
            updated_at_ms=_now_ms(),
        )
        return self._event_repository.update(updated)

    def bulk_transition_events(
        self,
        session_id: str,
        event_ids: list[str],
        *,
        target_state: EventState,
        assignee: str | None = None,
        due_date: str | None = None,
    ) -> list[MeetingEvent]:
        """여러 이벤트를 같은 상태로 한 번에 전이한다."""

        updated_items: list[MeetingEvent] = []
        for event_id in event_ids:
            updated_items.append(
                self.transition_event(
                    session_id,
                    event_id,
                    target_state=target_state,
                    assignee=assignee,
                    due_date=due_date,
                )
            )
        return updated_items

    def _get_event(self, session_id: str, event_id: str) -> MeetingEvent:
        event = self._event_repository.get_by_id(event_id)
        if event is None or event.session_id != session_id:
            raise ValueError("이벤트를 찾을 수 없습니다.")
        return event

    def _validate_transition(self, event: MeetingEvent, target_state: EventState) -> None:
        if event.state == target_state:
            return

        if event.event_type not in self._ALLOWED_TRANSITIONS:
            raise ValueError("이 이벤트 타입은 상태 전이를 지원하지 않습니다.")

        allowed = self._ALLOWED_TRANSITIONS[event.event_type].get(event.state, set())
        if target_state not in allowed:
            raise ValueError(
                f"허용되지 않는 상태 전이입니다: {event.event_type.value} {event.state.value} -> {target_state.value}"
            )

