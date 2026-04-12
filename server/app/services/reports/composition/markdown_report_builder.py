"""리포트 영역의 markdown report builder 서비스를 제공한다."""
from __future__ import annotations

from collections import defaultdict

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventType
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)


class MarkdownReportBuilder:
    """세션 데이터를 정제 전 raw Markdown 문서로 조립한다."""

    def build(
        self,
        session_id: str,
        events: list[MeetingEvent],
        speaker_transcript: list[SpeakerTranscriptSegment] | None = None,
        speaker_events: list[SpeakerAttributedEvent] | None = None,
        reference_transcript_lines: list[str] | None = None,
    ) -> str:
        """세션 이벤트와 화자 정보를 raw Markdown 문자열로 변환한다."""

        grouped_events = self._group_events(events)
        lines = [
            f"# Session Report: {session_id}",
            "",
            "## Raw Summary",
            f"- Total events: {len(events)}",
            f"- Questions: {len(grouped_events[EventType.QUESTION])}",
            f"- Decisions: {len(grouped_events[EventType.DECISION])}",
            f"- Action items: {len(grouped_events[EventType.ACTION_ITEM])}",
            f"- Risks: {len(grouped_events[EventType.RISK])}",
            "",
            "## Raw Event Log",
        ]

        self._append_event_log(lines, events)

        if speaker_transcript:
            lines.extend(["", "## Raw Speaker Transcript"])
            for segment in speaker_transcript:
                lines.append(
                    f"- [{segment.speaker_label}] "
                    f"({segment.start_ms}ms-{segment.end_ms}ms, confidence={segment.confidence:.3f}) "
                    f"{segment.text}"
                )

        if speaker_events:
            lines.extend(["", "## Raw Speaker Event Log"])
            for attributed_event in speaker_events:
                lines.append(
                    f"- [{attributed_event.event.event_type.value}] "
                    f"{attributed_event.speaker_label}: {attributed_event.event.title}"
                )

        if reference_transcript_lines:
            lines.extend(["", "## Raw Transcript"])
            lines.extend(f"- {line}" for line in reference_transcript_lines)

        return "\n".join(lines)

    @staticmethod
    def _group_events(events: list[MeetingEvent]) -> dict[EventType, list[MeetingEvent]]:
        grouped: dict[EventType, list[MeetingEvent]] = defaultdict(list)
        for event in events:
            grouped[event.event_type].append(event)
        return grouped

    def _append_event_log(
        self,
        lines: list[str],
        events: list[MeetingEvent],
    ) -> None:
        if not events:
            lines.append("- 없음")
            return

        for event in events:
            lines.append(f"- [{event.event_type.value}] {event.title}")
            lines.extend(self._build_event_metadata_lines(event))

    @staticmethod
    def _build_event_metadata_lines(event: MeetingEvent) -> list[str]:
        metadata_lines = [f"  - state: {event.state.value}"]
        if event.speaker_label:
            metadata_lines.append(f"  - speaker_label: {event.speaker_label}")
        if event.input_source:
            metadata_lines.append(f"  - input_source: {event.input_source}")
        if event.evidence_text:
            metadata_lines.append(f"  - evidence: {event.evidence_text}")
        elif event.body:
            metadata_lines.append(f"  - note: {event.body}")
        return metadata_lines
