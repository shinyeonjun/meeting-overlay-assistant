"""이벤트를 만들지 않는 회의 분석기."""

from __future__ import annotations

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer


class NoOpMeetingAnalyzer(MeetingAnalyzer):
    """MVP에서 실시간 이벤트 추출을 끌 때 사용하는 analyzer."""

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        return []
