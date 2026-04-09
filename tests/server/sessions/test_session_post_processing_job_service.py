"""세션 후처리 job 서비스 테스트."""

from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.infrastructure.persistence.postgresql.repositories.events.postgresql_event_repository import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_session_post_processing_job_repository import (
    PostgreSQLSessionPostProcessingJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.post_meeting.session_post_processing_job_service import (
    SessionPostProcessingJobService,
)
from server.app.services.reports.refinement import (
    TranscriptCorrectionStore,
)
from server.app.services.sessions.session_service import SessionService


class _InMemoryQueue:
    def __init__(self) -> None:
        self.job_ids: list[str] = []

    def publish(self, job_id: str) -> bool:
        self.job_ids.append(job_id)
        return True

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        del timeout_seconds
        if not self.job_ids:
            return None
        return self.job_ids.pop(0)


class _StubAudioPostprocessingService:
    def build_speaker_transcript(self, audio_path):
        del audio_path
        return [
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1200,
                text="결정은 다음 주에 다시 논의합시다.",
                confidence=0.93,
            ),
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_01",
                start_ms=1200,
                end_ms=2600,
                text="질문은 예산안을 누가 정리할까요?",
                confidence=0.91,
            ),
        ]


class _StubAnalyzer:
    def analyze(self, utterance):
        event_type = EventType.QUESTION if "질문" in utterance.text else EventType.DECISION
        state = EventState.OPEN if event_type == EventType.QUESTION else EventState.CONFIRMED
        return [
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=event_type,
                title=utterance.text,
                state=state,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                speaker_label=utterance.speaker_label,
                input_source=utterance.input_source,
            )
        ]


class _RecordingReportJobService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, bool]] = []

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ):
        self.calls.append((session_id, requested_by_user_id, dispatch))
        return None


class _StubNoteTranscriptCorrector:
    def correct(self, *, session_id: str, source_version: int, utterances):
        from server.app.services.reports.refinement import (
            TranscriptCorrectionDocument,
            TranscriptCorrectionItem,
        )

        items = []
        for utterance in utterances:
            items.append(
                TranscriptCorrectionItem(
                    utterance_id=utterance.id,
                    raw_text=utterance.text,
                    corrected_text=utterance.text.replace("寃곗젙", "결정"),
                    changed="寃곗젙" in utterance.text,
                    risk_flags=[],
                )
            )
        return TranscriptCorrectionDocument(
            session_id=session_id,
            source_version=source_version,
            model="stub-gemma",
            items=items,
        )


class TestSessionPostProcessingJobService:
    """dispatch와 claim/lease 계약을 검증한다."""

    def test_enqueue_for_session은_pending_job을_queue에_발행한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        queue = _InMemoryQueue()
        session_service = SessionService(session_repository)
        service = SessionPostProcessingJobService(
            repository=repository,
            session_repository=session_repository,
            job_queue=queue,
        )
        session = session_service.create_session_draft(
            title="후처리 큐 발행 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=True,
        )

        assert queue.job_ids == [job.id]
        assert service.wait_for_dispatched_job(0) == job.id
        refreshed_session = session_service.get_session(session.id)
        assert refreshed_session is not None
        assert refreshed_session.post_processing_status == "queued"

    def test_worker가_pending_job을_claim하면_lease와_attempt가_기록된다(
        self,
        isolated_database,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        session_service = SessionService(session_repository)
        service = SessionPostProcessingJobService(
            repository=repository,
            session_repository=session_repository,
        )
        session = session_service.create_session_draft(
            title="후처리 분산 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )

        claimed_jobs = service.claim_available_jobs(
            worker_id="worker-a",
            lease_duration_seconds=120,
            limit=1,
        )

        assert len(claimed_jobs) == 1
        claimed_job = claimed_jobs[0]
        assert claimed_job.status == "processing"
        assert claimed_job.claimed_by_worker_id == "worker-a"
        assert claimed_job.lease_expires_at is not None
        assert claimed_job.attempt_count == 1

    def test_process_job은_canonical_utterance와_event를_저장하고_report_job을_연결한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        job_repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        event_repository = PostgreSQLMeetingEventRepository(isolated_database)
        report_job_service = _RecordingReportJobService()
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)

        session = session_service.create_session_draft(
            title="후처리 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)

        recording_artifact = artifact_store.build_recording_artifact(
            session_id=session.id,
            input_source="system_audio",
        )
        recording_artifact.file_path.parent.mkdir(parents=True, exist_ok=True)
        recording_artifact.file_path.write_bytes(b"RIFF0000WAVEfmt ")

        service = SessionPostProcessingJobService(
            repository=job_repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            event_repository=event_repository,
            audio_postprocessing_service=_StubAudioPostprocessingService(),
            analyzer=_StubAnalyzer(),
            note_transcript_corrector=_StubNoteTranscriptCorrector(),
            report_generation_job_service=report_job_service,
            artifact_store=artifact_store,
            transcript_correction_store=correction_store,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)

        refreshed_session = session_service.get_session(session.id)
        utterances = utterance_repository.list_by_session(session.id)
        events = event_repository.list_by_session(session.id)
        correction_document = correction_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert refreshed_session is not None
        assert refreshed_session.post_processing_status == "completed"
        assert refreshed_session.canonical_transcript_version == 1
        assert refreshed_session.canonical_events_version == 1
        assert [item.transcript_source for item in utterances] == [
            "post_processed",
            "post_processed",
        ]
        assert [item.speaker_label for item in utterances] == [
            "SPEAKER_00",
            "SPEAKER_01",
        ]
        assert {item.event_source for item in events} == {"post_processed"}
        assert {item.event_type for item in events} == {
            EventType.DECISION,
            EventType.QUESTION,
        }
        assert correction_document is not None
        assert correction_document.model == "stub-gemma"
        assert len(correction_document.items) == 2
        assert report_job_service.calls == [(session.id, None, True)]
