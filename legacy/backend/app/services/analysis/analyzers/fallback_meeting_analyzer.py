"""분석기 fallback 조합기."""

from __future__ import annotations

from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.models.utterance import Utterance
from backend.app.services.analysis.analyzers.analyzer import MeetingAnalyzer


class FallbackMeetingAnalyzer(MeetingAnalyzer):
    """여러 분석기를 순서대로 시도하고 첫 결과를 채택한다."""

    def __init__(self, analyzers: tuple[MeetingAnalyzer, ...]) -> None:
        self._analyzers = analyzers

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        """분석기를 순회하며 첫 유효 결과를 반환한다."""
        for analyzer in self._analyzers:
            events = analyzer.analyze(utterance)
            if events:
                return events
        return []
