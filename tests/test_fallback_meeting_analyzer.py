"""Fallback 분석기 테스트."""

from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.models.utterance import Utterance
from backend.app.domain.shared.enums import EventType
from backend.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from backend.app.services.analysis.analyzers.fallback_meeting_analyzer import (
    FallbackMeetingAnalyzer,
)


class TestFallbackMeetingAnalyzer:
    """분석기 fallback 동작 테스트."""

    def test_앞선_분석기가_빈결과면_다음_분석기로_대체한다(self):
        utterance = Utterance.create(
            session_id="session-test",
            seq_num=1,
            start_ms=0,
            end_ms=1000,
            text="이번 배포에서는 이 수정은 제외합시다.",
            confidence=0.95,
        )
        analyzer = FallbackMeetingAnalyzer(
            analyzers=(
                StubAnalyzer(events=[]),
                StubAnalyzer(
                    events=[
                        MeetingEvent.create(
                            session_id="session-test",
                            event_type=EventType.DECISION,
                            title="이번 배포에서는 이 수정은 제외합시다.",
                            body=None,
                            state="confirmed",
                            priority=85,
                            source_utterance_id="utt-1",
                        )
                    ]
                ),
            )
        )

        events = analyzer.analyze(utterance)

        assert len(events) == 1
        assert events[0].event_type == EventType.DECISION


class StubAnalyzer(MeetingAnalyzer):
    """테스트용 analyzer."""

    def __init__(self, events: list[MeetingEvent]) -> None:
        self._events = events

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        del utterance
        return self._events
