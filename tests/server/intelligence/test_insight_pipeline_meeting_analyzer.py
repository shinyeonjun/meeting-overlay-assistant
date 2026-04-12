"""공통 영역의 test insight pipeline meeting analyzer 동작을 검증한다."""
from __future__ import annotations

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.analysis.analyzers.insight_pipeline_meeting_analyzer import (
    InsightPipelineMeetingAnalyzer,
)
from tests.fixtures.support.sample_inputs import build_utterance


class TestInsightPipelineMeetingAnalyzer:
    """stage 결과를 병합하는 조합형 분석기 테스트."""

    def test_동일_이벤트는_중복없이_병합한다(self):
        utterance = build_utterance("이거 사파리에서만 재현되는 거 맞아요?")
        stage_one_event = MeetingEvent.create(
            session_id=utterance.session_id,
            event_type=EventType.QUESTION,
            title=utterance.text,
            body=None,
            state=EventState.OPEN,
            priority=EventPriority.QUESTION,
            source_utterance_id=utterance.id,
        )
        stage_two_event = MeetingEvent.create(
            session_id=utterance.session_id,
            event_type=EventType.QUESTION,
            title=utterance.text,
            body="사파리 전용 이슈 확인이 필요합니다.",
            state=EventState.OPEN,
            priority=EventPriority.RISK,
            source_utterance_id=utterance.id,
        )

        analyzer = InsightPipelineMeetingAnalyzer(
            analyzers=(
                StubAnalyzer((stage_one_event,)),
                StubAnalyzer((stage_two_event,)),
            )
        )

        events = analyzer.analyze(utterance)

        assert len(events) == 1
        assert events[0].body == "사파리 전용 이슈 확인이 필요합니다."
        assert events[0].event_type == EventType.QUESTION

    def test_서로_다른_이벤트는_각각_유지한다(self):
        utterance = build_utterance("민수가 금요일까지 수정안 정리해 주세요.")
        question_event = MeetingEvent.create(
            session_id=utterance.session_id,
            event_type=EventType.QUESTION,
            title="이 일정 맞나요?",
            body=None,
            state=EventState.OPEN,
            priority=EventPriority.QUESTION,
            source_utterance_id=utterance.id,
        )
        action_event = MeetingEvent.create(
            session_id=utterance.session_id,
            event_type=EventType.ACTION_ITEM,
            title=utterance.text,
            body=None,
            state=EventState.OPEN,
            priority=EventPriority.ACTION_ITEM,
            source_utterance_id=utterance.id,
        )

        analyzer = InsightPipelineMeetingAnalyzer(
            analyzers=(
                StubAnalyzer((question_event,)),
                StubAnalyzer((action_event,)),
            )
        )

        events = analyzer.analyze(utterance)

        assert len(events) == 2
        assert {event.event_type for event in events} == {
            EventType.QUESTION,
            EventType.ACTION_ITEM,
        }

    def test_stage가_비어있으면_예외를_발생한다(self):
        try:
            InsightPipelineMeetingAnalyzer(analyzers=())
        except ValueError:
            return
        raise AssertionError("stage가 비어있으면 ValueError를 던져야 합니다.")


class StubAnalyzer(MeetingAnalyzer):
    """테스트용 고정 응답 분석기."""

    def __init__(self, events: tuple[MeetingEvent, ...]) -> None:
        self._events = events

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        return list(self._events)
