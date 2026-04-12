"""화자 분리 영역의 test speaker event projection service 동작을 검증한다."""
from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)


class _FakeAnalyzer(MeetingAnalyzer):
    def analyze(self, utterance):
        return [
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.QUESTION,
                title=utterance.text,
                body=None,
                state=EventState.OPEN,
                priority=EventPriority.QUESTION,
                source_utterance_id=utterance.id,
            )
        ]


class TestSpeakerEventProjectionService:
    """SpeakerEventProjectionService 동작을 검증한다."""
    def test_화자_전사를_화자_이벤트로_투영한다(self):
        service = SpeakerEventProjectionService(analyzer=_FakeAnalyzer())
        transcript = [
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1000,
                text="이거 사파리에서만 재현되는 거 맞아요?",
                confidence=0.91,
            )
        ]

        events = service.project(session_id="session-test", speaker_transcript=transcript)

        assert len(events) == 1
        assert isinstance(events[0], SpeakerAttributedEvent)
        assert events[0].speaker_label == "SPEAKER_00"
        assert events[0].event.event_type == EventType.QUESTION
