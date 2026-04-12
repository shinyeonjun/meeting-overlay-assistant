"""화자 분리 영역의 test speaker label persistence 동작을 검증한다."""
from __future__ import annotations

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import (
    AudioSource,
    EventPriority,
    EventState,
    EventType,
    SessionMode,
)
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerEventProjectionService,
)


class FakeAnalyzer:
    """FakeAnalyzer 동작을 검증한다."""
    def analyze(self, utterance):
        return [
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.QUESTION,
                title=utterance.text,
                state=EventState.CONFIRMED,
                priority=EventPriority.QUESTION,
                source_utterance_id=utterance.id,
            )
        ]


class TestSpeakerLabelPersistence:
    """SpeakerLabelPersistence 동작을 검증한다."""
    def test_projection_이벤트에_speaker_label이_들어간다(self):
        service = SpeakerEventProjectionService(analyzer=FakeAnalyzer())

        result = service.project(
            session_id="session-1",
            speaker_transcript=[
                SpeakerTranscriptSegment(
                    speaker_label="SPEAKER_00",
                    start_ms=0,
                    end_ms=1000,
                    text="이거 맞아요?",
                    confidence=0.9,
                )
            ],
        )

        assert result[0].speaker_label == "SPEAKER_00"
        assert result[0].event.speaker_label == "SPEAKER_00"

    def test_repository가_speaker_label을_저장하고_조회한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        session = session_repository.save(
            MeetingSession.start(
                title="speaker label test",
                mode=SessionMode.MEETING,
                source=AudioSource.FILE,
            )
        )

        repository = PostgreSQLMeetingEventRepository(isolated_database)
        event = MeetingEvent.create(
            session_id=session.id,
            event_type=EventType.DECISION,
            title="이번 배포에서는 제외합니다.",
            state=EventState.CONFIRMED,
            priority=EventPriority.DECISION,
            source_utterance_id=None,
            speaker_label="SPEAKER_01",
        )

        repository.save(event)
        loaded = repository.list_by_session(session.id)

        assert loaded[0].speaker_label == "SPEAKER_01"
