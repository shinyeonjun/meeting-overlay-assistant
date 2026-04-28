from datetime import datetime

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)


class _RenewLeaseRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def renew_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_expires_at: str,
    ) -> bool:
        self.calls.append(
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "lease_expires_at": lease_expires_at,
            }
        )
        return True


class _UnusedSessionPostProcessingJobRepository:
    def get_latest_by_sessions(self, session_ids):
        del session_ids
        return {}


class _UnusedNoteCorrectionJobRepository:
    def get_latest_by_sessions(self, session_ids):
        del session_ids
        return {}


class _UnusedReportService:
    pass


def test_report_generation_job_service_renew_job_lease_sets_new_expiration() -> None:
    repository = _RenewLeaseRepository()
    service = ReportGenerationJobService(
        repository=repository,
        session_post_processing_job_repository=_UnusedSessionPostProcessingJobRepository(),
        note_correction_job_repository=_UnusedNoteCorrectionJobRepository(),
        report_service=_UnusedReportService(),
    )
    job = ReportGenerationJob.create_pending(
        session_id="session-1",
        recording_artifact_id=None,
        recording_path=None,
    )

    renewed = service.renew_job_lease(
        job_id=job.id,
        worker_id="worker-a",
        lease_duration_seconds=120,
    )

    assert renewed is True
    assert len(repository.calls) == 1
    call = repository.calls[0]
    assert call["job_id"] == job.id
    assert call["worker_id"] == "worker-a"
    assert isinstance(call["lease_expires_at"], str)
    datetime.fromisoformat(call["lease_expires_at"])
