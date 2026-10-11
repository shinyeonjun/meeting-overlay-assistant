"""회의 분석기 인터페이스."""

from __future__ import annotations

from typing import Protocol

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance


class MeetingAnalyzer(Protocol):
    """발화를 구조화 이벤트로 바꾸는 분석기 인터페이스."""

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        """발화를 분석해 이벤트 목록을 반환한다."""
