"""리포트 영역의 test report generation job service 동작을 검증한다."""
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_generation_job_repository import (
    PostgreSQLReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)
from server.app.services.sessions.session_service import SessionService


class _UnusedReportService:
    pass


class _UnusedNoteCorrectionJobRepository:
    def get_latest_by_sessions(self, session_ids):
        del session_ids
        return {}


class _InMemoryQueue:
    def __init__(self) -> None:
        self.job_ids: list[str] = []

    def publish(self, job_id: str) -> bool:
        self.job_ids.append(job_id)
        return True

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        if not self.job_ids:
            return None
        return self.job_ids.pop(0)


class _FailingQueue:
    def __init__(self) -> None:
        self.published_job_ids: list[str] = []

    def publish(self, job_id: str) -> bool:
        self.published_job_ids.append(job_id)
        return False

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        return None


class TestReportGenerationJobService:
    """claim/lease와 dispatch 계약을 검증한다."""

    def test_worker가_pending_job을_claim하면_lease와_attempt가_기록된다(
        self,
        isolated_database,
    ):
        repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
        service = ReportGenerationJobService(
            repository=repository,
            note_correction_job_repository=_UnusedNoteCorrectionJobRepository(),
            report_service=_UnusedReportService(),
        )
        session = session_service.create_session_draft(
            title="분산 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        job = repository.save(
            ReportGenerationJob.create_pending(
                session_id=session.id,
                recording_artifact_id="recordings/test-session/system_audio.wav",
                recording_path="recording.wav",
                requested_by_user_id=None,
            )
        )

        claimed_jobs = service.claim_available_jobs(
            worker_id="worker-a",
            lease_duration_seconds=120,
            limit=1,
        )

        assert len(claimed_jobs) == 1
        claimed_job = claimed_jobs[0]
        assert claimed_job.id == job.id
        assert claimed_job.status == "processing"
        assert claimed_job.claimed_by_worker_id == "worker-a"
        assert claimed_job.lease_expires_at is not None
        assert claimed_job.attempt_count == 1

    def test_lease가_만료된_processing_job은_다시_claim할_수_있다(
        self,
        isolated_database,
    ):
        repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
        service = ReportGenerationJobService(
            repository=repository,
            note_correction_job_repository=_UnusedNoteCorrectionJobRepository(),
            report_service=_UnusedReportService(),
        )
        session = session_service.create_session_draft(
            title="lease 재점유 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        job = repository.save(
            ReportGenerationJob.create_pending(
                session_id=session.id,
                recording_artifact_id="recordings/test-session/system_audio.wav",
                recording_path="recording.wav",
                requested_by_user_id=None,
            )
        )
        repository.update(
            job.mark_processing(
                claimed_by_worker_id="worker-old",
                lease_expires_at="2000-01-01T00:00:00+00:00",
                started_at="2000-01-01T00:00:00+00:00",
            )
        )

        claimed_jobs = service.claim_available_jobs(
            worker_id="worker-new",
            lease_duration_seconds=120,
            limit=1,
        )

        assert len(claimed_jobs) == 1
        reclaimed_job = claimed_jobs[0]
        assert reclaimed_job.status == "processing"
        assert reclaimed_job.claimed_by_worker_id == "worker-new"
        assert reclaimed_job.attempt_count == 2

    def test_enqueue_for_session은_pending_job을_queue에_발행한다(self, isolated_database):
        repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
        queue = _InMemoryQueue()
        service = ReportGenerationJobService(
            repository=repository,
            note_correction_job_repository=_UnusedNoteCorrectionJobRepository(),
            report_service=_UnusedReportService(),
            job_queue=queue,
        )
        session = session_service.create_session_draft(
            title="큐 발행 테스트",
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

    def test_dispatch가_실패해도_job은_pending으로_남는다(self, isolated_database):
        repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
        queue = _FailingQueue()
        service = ReportGenerationJobService(
            repository=repository,
            note_correction_job_repository=_UnusedNoteCorrectionJobRepository(),
            report_service=_UnusedReportService(),
            job_queue=queue,
        )
        session = session_service.create_session_draft(
            title="dispatch failure 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=True,
        )

        assert queue.published_job_ids == [job.id]
        latest_job = service.get_latest_job(session.id)
        assert latest_job is not None
        assert latest_job.status == "pending"
