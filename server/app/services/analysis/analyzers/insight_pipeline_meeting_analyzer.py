"""공통 영역의 insight pipeline meeting analyzer 서비스를 제공한다."""
from __future__ import annotations

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer


class InsightPipelineMeetingAnalyzer(MeetingAnalyzer):
    """여러 분석기 결과를 순차 병합해 최종 이벤트를 만든다."""

    def __init__(self, analyzers: tuple[MeetingAnalyzer, ...]) -> None:
        if not analyzers:
            raise ValueError("insight pipeline analyzer는 최소 1개 이상의 stage가 필요합니다.")
        self._analyzers = analyzers

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        """stage 순서대로 결과를 누적하고 중복 이벤트를 병합한다."""
        merged_events: list[MeetingEvent] = []
        for analyzer in self._analyzers:
            for candidate in analyzer.analyze(utterance):
                self._merge_candidate(merged_events, candidate)
        return merged_events

    @staticmethod
    def _merge_candidate(events: list[MeetingEvent], candidate: MeetingEvent) -> None:
        for index, existing in enumerate(events):
            if not existing.can_merge_with(candidate):
                continue
            events[index] = existing.merge_with(candidate)
            return
        events.append(candidate)
