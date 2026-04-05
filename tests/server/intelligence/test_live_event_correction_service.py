"""비동기 live event correction 테스트."""

from __future__ import annotations

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.services.analysis.correction.live_event_correction_service import (
    AsyncLiveEventCorrectionService,
)


class _FakeAnalyzer:
    def __init__(self, events: list[MeetingEvent]) -> None:
        self._events = events

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        return self._events


class _FakeEventService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def apply_source_utterance_corrections(
        self,
        *,
        session_id: str,
        source_utterance_id: str,
        corrected_events: list[MeetingEvent],
        target_event_types: tuple[EventType, ...],
        connection,
    ) -> list[MeetingEvent]:
        self.calls.append(
            {
                "session_id": session_id,
                "source_utterance_id": source_utterance_id,
                "corrected_events": corrected_events,
                "target_event_types": target_event_types,
                "connection": connection,
            }
        )
        return corrected_events


class _FakeTransactionManager:
    class _ConnectionContext:
        def __enter__(self):
            return "fake-connection"

        def __exit__(self, exc_type, exc, tb):
            return False

    def transaction(self):
        return self._ConnectionContext()


def test_대상_발화면_교정_서비스가_필터된_이벤트를_적용한다() -> None:
    utterance = Utterance.create(
        session_id="session-1",
        seq_num=1,
        start_ms=0,
        end_ms=1000,
        text="이번 배포에서는 이 수정은 제외합시다.",
        confidence=0.91,
    )
    corrected_events = [
        MeetingEvent.create(
            session_id="session-1",
            event_type=EventType.DECISION,
            title="이번 배포에서는 이 수정은 제외",
            body=None,
            state=EventState.CONFIRMED,
            priority=EventPriority.DECISION,
            source_utterance_id=utterance.id,
        ),
        MeetingEvent.create(
            session_id="session-1",
            event_type=EventType.TOPIC,
            title="배포 범위 논의",
            body=None,
            state=EventState.ACTIVE,
            priority=EventPriority.TOPIC,
            source_utterance_id=utterance.id,
        ),
    ]
    event_service = _FakeEventService()
    service = AsyncLiveEventCorrectionService(
        analyzer=_FakeAnalyzer(corrected_events),
        event_service=event_service,
        transaction_manager=_FakeTransactionManager(),
        target_event_types=(EventType.DECISION, EventType.ACTION_ITEM),
        min_utterance_confidence=0.7,
        min_text_length=8,
        max_workers=1,
    )

    persisted_events = service.correct(utterance)

    assert len(persisted_events) == 1
    assert persisted_events[0].event_type == EventType.DECISION
    assert len(event_service.calls) == 1
    assert event_service.calls[0]["source_utterance_id"] == utterance.id


def test_낮은_confidence_발화는_submit하지_않는다() -> None:
    utterance = Utterance.create(
        session_id="session-1",
        seq_num=1,
        start_ms=0,
        end_ms=1000,
        text="짧다",
        confidence=0.4,
    )
    event_service = _FakeEventService()
    service = AsyncLiveEventCorrectionService(
        analyzer=_FakeAnalyzer([]),
        event_service=event_service,
        transaction_manager=_FakeTransactionManager(),
        target_event_types=(EventType.DECISION,),
        min_utterance_confidence=0.7,
        min_text_length=8,
        max_workers=1,
    )

    assert service._should_submit(utterance) is False
