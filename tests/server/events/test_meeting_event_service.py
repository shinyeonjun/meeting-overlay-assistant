"""MeetingEventService 테스트."""

from __future__ import annotations

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.services.events.meeting_event_service import MeetingEventService


class _FakeEventRepository:
    def __init__(self, existing_events: list[MeetingEvent] | None = None) -> None:
        self.existing_events = list(existing_events or [])
        self.saved: list[MeetingEvent] = []
        self.updated: list[MeetingEvent] = []
        self.deleted: list[str] = []
        self.merge_target: MeetingEvent | None = None

    def find_merge_target(self, candidate: MeetingEvent, *, connection=None):
        del candidate, connection
        return self.merge_target

    def list_by_source_utterance(
        self,
        session_id: str,
        source_utterance_id: str,
        *,
        insight_scope: str,
        connection=None,
    ) -> list[MeetingEvent]:
        del session_id, source_utterance_id, insight_scope, connection
        return list(self.existing_events)

    def save(self, event: MeetingEvent, *, connection=None) -> MeetingEvent:
        del connection
        self.saved.append(event)
        return event

    def update(self, event: MeetingEvent, *, connection=None) -> MeetingEvent:
        del connection
        self.updated.append(event)
        return event

    def delete(self, event_id: str, *, connection=None) -> None:
        del connection
        self.deleted.append(event_id)


def _build_event(
    *,
    session_id: str = "session-1",
    event_type: EventType,
    title: str,
    state: EventState,
    source_utterance_id: str | None = "utt-1",
    body: str | None = None,
) -> MeetingEvent:
    return MeetingEvent.create(
        session_id=session_id,
        event_type=event_type,
        title=title,
        body=body,
        state=state,
        source_utterance_id=source_utterance_id,
    )


def test_save_or_merge가_same_source_event를_업데이트한다() -> None:
    existing = _build_event(
        event_type=EventType.DECISION,
        title="기존 결정",
        body="old",
        state=EventState.CONFIRMED,
    )
    candidate = _build_event(
        event_type=EventType.DECISION,
        title="새 결정",
        body="new",
        state=EventState.UPDATED,
    )
    repository = _FakeEventRepository(existing_events=[existing])
    service = MeetingEventService(repository)

    persisted = service.save_or_merge(candidate)

    assert persisted.title == "새 결정"
    assert persisted.body == "new"
    assert repository.saved == []
    assert len(repository.updated) == 1


def test_apply_source_utterance_corrections가_기존_이벤트를_갱신하고_누락된_타입은_삭제한다() -> None:
    existing_decision = _build_event(
        event_type=EventType.DECISION,
        title="기존 결정",
        body="old",
        state=EventState.CONFIRMED,
    )
    existing_action = _build_event(
        event_type=EventType.ACTION_ITEM,
        title="기존 액션",
        body="old action",
        state=EventState.OPEN,
    )
    corrected_decision = _build_event(
        event_type=EventType.DECISION,
        title="수정된 결정",
        body="new",
        state=EventState.UPDATED,
    )
    repository = _FakeEventRepository(existing_events=[existing_decision, existing_action])
    service = MeetingEventService(repository)

    persisted = service.apply_source_utterance_corrections(
        session_id="session-1",
        source_utterance_id="utt-1",
        corrected_events=[corrected_decision],
        target_event_types=(EventType.DECISION, EventType.ACTION_ITEM),
    )

    assert len(persisted) == 1
    assert persisted[0].id == existing_decision.id
    assert persisted[0].title == "수정된 결정"
    assert repository.deleted == [existing_action.id]


def test_apply_source_utterance_corrections가_없는_이벤트는_새로_저장한다() -> None:
    corrected_question = _build_event(
        event_type=EventType.QUESTION,
        title="신규 질문",
        body="body",
        state=EventState.OPEN,
    )
    repository = _FakeEventRepository(existing_events=[])
    service = MeetingEventService(repository)

    persisted = service.apply_source_utterance_corrections(
        session_id="session-1",
        source_utterance_id="utt-1",
        corrected_events=[corrected_question],
        target_event_types=(EventType.QUESTION,),
    )

    assert persisted == [corrected_question]
    assert repository.saved == [corrected_question]
