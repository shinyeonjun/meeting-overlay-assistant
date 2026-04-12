"""리포트 영역의 test markdown report builder 동작을 검증한다."""
from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.markdown_report_builder import (
    MarkdownReportBuilder,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)


class TestMarkdownReportBuilder:
    """정제 전 raw Markdown 조립 결과를 검증한다."""

    def test_이벤트_raw_로그와_메타데이터를_조립한다(self):
        builder = MarkdownReportBuilder()
        events = [
            MeetingEvent.create(
                session_id="session-test",
                event_type=EventType.DECISION,
                title="발표 일정은 다음 주 수요일로 확정됐다.",
                body=None,
                state=EventState.CONFIRMED,
                priority=EventPriority.DECISION,
                source_utterance_id="utt-1",
                input_source="system_audio",
                evidence_text="이번 발표는 다음 주 수요일로 확정합시다.",
            ),
            MeetingEvent.create(
                session_id="session-test",
                event_type=EventType.RISK,
                title="일정이 밀리면 QA가 부족해질 수 있다.",
                body=None,
                state=EventState.OPEN,
                priority=EventPriority.RISK,
                source_utterance_id="utt-2",
                evidence_text="일정이 밀리면 QA가 부족해질 수 있다.",
            ),
        ]
        speaker_transcript = [
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1200,
                text="이번 발표는 다음 주 수요일로 확정합시다.",
                confidence=0.91,
            )
        ]
        speaker_events = [
            SpeakerAttributedEvent(
                speaker_label="SPEAKER_00",
                event=MeetingEvent.create(
                    session_id="session-test",
                    event_type=EventType.QUESTION,
                    title="이번 발표는 다음 주 수요일로 확정해도 되나요?",
                    body=None,
                    state=EventState.OPEN,
                    priority=EventPriority.QUESTION,
                    source_utterance_id="utt-3",
                ),
            )
        ]

        markdown = builder.build(
            session_id="session-test",
            events=events,
            speaker_transcript=speaker_transcript,
            speaker_events=speaker_events,
        )

        assert "# Session Report: session-test" in markdown
        assert "## Raw Summary" in markdown
        assert "- Total events: 2" in markdown
        assert "## Raw Event Log" in markdown
        assert "[decision] 발표 일정은 다음 주 수요일로 확정됐다." in markdown
        assert "  - state: confirmed" in markdown
        assert "  - input_source: system_audio" in markdown
        assert "  - evidence: 이번 발표는 다음 주 수요일로 확정합시다." in markdown
        assert "  - evidence: 일정이 밀리면 QA가 부족해질 수 있다." in markdown
        assert "## Raw Speaker Transcript" in markdown
        assert "## Raw Speaker Event Log" in markdown
        assert "[question] SPEAKER_00: 이번 발표는 다음 주 수요일로 확정해도 되나요?" in markdown

    def test_이벤트가_없으면_raw_이벤트_로그에_없음으로_표시한다(self):
        builder = MarkdownReportBuilder()

        markdown = builder.build(session_id="session-empty", events=[])

        assert "## Raw Summary" in markdown
        assert "## Raw Event Log" in markdown
        assert markdown.count("- 없음") >= 1
