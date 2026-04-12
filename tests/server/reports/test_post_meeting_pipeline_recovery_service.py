"""post-meeting 파이프라인 recovery 서비스 테스트."""

from __future__ import annotations

from types import SimpleNamespace

from server.app.domain.models.note_correction_job import NoteCorrectionJob
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.services.reports.jobs.post_meeting_pipeline_recovery_service import (
    PostMeetingPipelineRecoveryService,
)
from server.app.services.reports.report_models import FinalReportStatus


class _SessionRepository:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def list_recent(self, *, limit: int = 50, **kwargs):
        del kwargs
        return self._sessions[:limit]


class _SessionPostProcessingJobService:
    def __init__(self, latest_jobs):
        self._latest_jobs = latest_jobs
        self.enqueued = []
        self.dispatched = []

    def get_latest_job(self, session_id: str):
        return self._latest_jobs.get(session_id)

    def enqueue_for_session(self, *, session_id: str, requested_by_user_id=None, dispatch=True):
        self.enqueued.append((session_id, requested_by_user_id, dispatch))
        return None

    def dispatch_job(self, job_id: str) -> bool:
        self.dispatched.append(job_id)
        return True


class _NoteCorrectionJobService:
    def __init__(self, latest_jobs):
        self._latest_jobs = latest_jobs
        self.enqueued = []
        self.dispatched = []

    def get_latest_job(self, session_id: str):
        return self._latest_jobs.get(session_id)

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        source_version: int,
        requested_by_user_id=None,
        dispatch=True,
    ):
        self.enqueued.append((session_id, source_version, requested_by_user_id, dispatch))
        return None

    def dispatch_job(self, job_id: str) -> bool:
        self.dispatched.append(job_id)
        return True


class _ReportGenerationJobService:
    def __init__(self, statuses, latest_jobs):
        self._statuses = statuses
        self._latest_jobs = latest_jobs
        self.enqueued = []
        self.dispatched = []

    def build_final_status(self, *, session):
        return self._statuses[session.id]

    def get_latest_job(self, session_id: str):
        return self._latest_jobs.get(session_id)

    def enqueue_for_session(self, *, session_id: str, requested_by_user_id=None, dispatch=True):
        self.enqueued.append((session_id, requested_by_user_id, dispatch))
        return None

    def dispatch_job(self, job_id: str) -> bool:
        self.dispatched.append(job_id)
        return True


def _build_final_status(*, session_id: str, pipeline_stage: str, status: str = "pending"):
    return FinalReportStatus(
        session_id=session_id,
        status=status,
        pipeline_stage=pipeline_stage,
        report_count=0,
    )


def test_recovery_requeues_failed_note_correction_job():
    session = SimpleNamespace(
        id="session-note",
        canonical_transcript_version=3,
    )
    note_job = NoteCorrectionJob.create_pending(
        session_id=session.id,
        source_version=3,
    ).mark_processing(
        claimed_by_worker_id="worker-old",
        lease_expires_at="2000-01-01T00:00:00+00:00",
        started_at="2000-01-01T00:00:00+00:00",
    ).mark_failed("timeout")

    recovery = PostMeetingPipelineRecoveryService(
        session_repository=_SessionRepository([session]),
        session_post_processing_job_service=_SessionPostProcessingJobService({}),
        note_correction_job_service=_NoteCorrectionJobService({session.id: note_job}),
        report_generation_job_service=_ReportGenerationJobService(
            {session.id: _build_final_status(session_id=session.id, pipeline_stage="note_correction")},
            {},
        ),
        max_attempts=3,
    )

    summary = recovery.recover(limit=10)

    assert summary.requeued_note_correction_jobs == 1
    assert recovery._note_correction_job_service.enqueued == [(session.id, 3, None, True)]


def test_recovery_dispatches_stalled_report_generation_job():
    session = SimpleNamespace(
        id="session-report",
        canonical_transcript_version=4,
    )
    report_job = ReportGenerationJob.create_pending(
        session_id=session.id,
        recording_artifact_id=None,
        recording_path=None,
    ).mark_processing(
        claimed_by_worker_id="worker-old",
        lease_expires_at="2000-01-01T00:00:00+00:00",
        started_at="2000-01-01T00:00:00+00:00",
    )

    report_service = _ReportGenerationJobService(
        {session.id: _build_final_status(session_id=session.id, pipeline_stage="report_generation")},
        {session.id: report_job},
    )
    recovery = PostMeetingPipelineRecoveryService(
        session_repository=_SessionRepository([session]),
        session_post_processing_job_service=_SessionPostProcessingJobService({}),
        note_correction_job_service=_NoteCorrectionJobService({}),
        report_generation_job_service=report_service,
        max_attempts=3,
    )

    summary = recovery.recover(limit=10)

    assert summary.requeued_report_jobs == 1
    assert report_service.dispatched == [report_job.id]


def test_recovery_skips_legacy_completed_session():
    session = SimpleNamespace(
        id="session-legacy",
        canonical_transcript_version=1,
    )
    recovery = PostMeetingPipelineRecoveryService(
        session_repository=_SessionRepository([session]),
        session_post_processing_job_service=_SessionPostProcessingJobService({}),
        note_correction_job_service=_NoteCorrectionJobService({}),
        report_generation_job_service=_ReportGenerationJobService(
            {session.id: _build_final_status(session_id=session.id, pipeline_stage="completed", status="completed")},
            {},
        ),
        max_attempts=3,
    )

    summary = recovery.recover(limit=10)

    assert summary.requeued_post_processing_jobs == 0
    assert summary.requeued_note_correction_jobs == 0
    assert summary.requeued_report_jobs == 0
