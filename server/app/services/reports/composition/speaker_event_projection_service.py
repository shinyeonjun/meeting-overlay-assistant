"""리포트 영역의 speaker event projection service 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass, replace

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)


@dataclass(frozen=True)
class SpeakerAttributedEvent:
    """화자 라벨이 붙은 이벤트 표현."""

    speaker_label: str
    event: MeetingEvent


class SpeakerEventProjectionService:
    """화자 전사 결과를 analyzer에 다시 태워 화자별 이벤트를 만든다."""

    def __init__(self, analyzer: MeetingAnalyzer) -> None:
        self._analyzer = analyzer

    def project(
        self,
        session_id: str,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> list[SpeakerAttributedEvent]:
        """화자 전사 목록을 화자-이벤트 목록으로 변환한다."""

        attributed_events: list[SpeakerAttributedEvent] = []
        for index, segment in enumerate(speaker_transcript, start=1):
            utterance = Utterance.create(
                session_id=session_id,
                seq_num=index,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=segment.text,
                confidence=segment.confidence,
            )
            events = self._analyzer.analyze(utterance)
            for event in events:
                attributed_event = replace(
                    event,
                    speaker_label=segment.speaker_label,
                    insight_scope="report",
                )
                attributed_events.append(
                    SpeakerAttributedEvent(
                        speaker_label=segment.speaker_label,
                        event=attributed_event,
                    )
                )
        return attributed_events
