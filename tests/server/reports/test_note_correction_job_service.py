"""노트 correction job 서비스 테스트."""

from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_note_correction_job_repository import (
    PostgreSQLNoteCorrectionJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.reports.jobs.note_correction_job_service import (
    NoteCorrectionJobService,
)
from server.app.services.reports.refinement import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionItem,
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


class _StubCorrector:
    def correct(self, *, session_id: str, source_version: int, utterances):
        return TranscriptCorrectionDocument(
            session_id=session_id,
            source_version=source_version,
            model="stub-corrector",
            items=[
                TranscriptCorrectionItem(
                    utterance_id=utterance.id,
                    raw_text=utterance.text,
                    corrected_text=f"{utterance.text} 수정",
                    changed=True,
                    risk_flags=[],
                )
                for utterance in utterances
            ],
        )


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


class TestNoteCorrectionJobService:
    def test_enqueue_for_session이_pending_job을_큐에_발행한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        queue = _InMemoryQueue()
        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            job_queue=queue,
        )
        session = session_service.create_session_draft(
            title="노트 보정 큐 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=0,
            requested_by_user_id=None,
            dispatch=True,
        )

        assert queue.job_ids == [job.id]
        assert service.wait_for_dispatched_job(0) == job.id

    def test_process_job이_correction을_저장하고_report_job을_연결한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        report_job_service = _RecordingReportJobService()

        session = session_service.create_session_draft(
            title="노트 보정 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="원본 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        document = correction_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert document is not None
        assert document.model == "stub-corrector"
        assert [item.corrected_text for item in document.items] == ["원본 발화 수정"]
        assert report_job_service.calls == [(session.id, None, True)]

    def test_stale_source_version_job은_건너뛰고_report를_생성하지_않는다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        report_job_service = _RecordingReportJobService()

        session = session_service.create_session_draft(
            title="stale correction 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            report_generation_job_service=report_job_service,
        )

        stale_job = service.enqueue_for_session(
            session_id=session.id,
            source_version=0,
            dispatch=False,
        )
        processed_job = service.process_job(stale_job.id)

        assert processed_job.status == "completed"
        assert correction_store.load(session_id=session.id) is None
        assert report_job_service.calls == []
