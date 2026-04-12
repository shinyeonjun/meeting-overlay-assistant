"""리포트 생성 job 생명주기 helper."""

from __future__ import annotations

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)
from server.app.services.audio.io.session_recording import (
    find_session_recording_artifact,
)
from server.app.services.reports.jobs.helpers.time_utils import (
    utc_after_seconds_iso,
    utc_now_iso,
)


def enqueue_or_reuse_job(
    *,
    session_id: str,
    requested_by_user_id: str | None,
    dispatch: bool,
    repository: ReportGenerationJobRepository,
    artifact_store: LocalArtifactStore,
    dispatch_job,
) -> ReportGenerationJob:
    """세션용 최신 pending job을 재사용하거나 새로 만든다."""

    latest_job = repository.get_latest_by_session(session_id)
    if latest_job is not None and latest_job.status in {"pending", "processing"}:
        if dispatch and latest_job.status == "pending":
            dispatch_job(latest_job.id)
        return latest_job

    recording_artifact = find_session_recording_artifact(
        session_id,
        artifact_store=artifact_store,
    )
    job = ReportGenerationJob.create_pending(
        session_id=session_id,
        recording_artifact_id=(
            recording_artifact.artifact_id if recording_artifact is not None else None
        ),
        recording_path=(
            str(recording_artifact.file_path) if recording_artifact is not None else None
        ),
        requested_by_user_id=requested_by_user_id,
    )
    saved_job = repository.save(job)
    if dispatch:
        dispatch_job(saved_job.id)
    return saved_job


def claim_jobs_for_worker(
    *,
    repository: ReportGenerationJobRepository,
    worker_id: str,
    lease_duration_seconds: int,
    limit: int,
) -> list[ReportGenerationJob]:
    """worker가 처리 가능한 job을 claim한다."""

    return repository.claim_available(
        worker_id=worker_id,
        lease_expires_at=utc_after_seconds_iso(lease_duration_seconds),
        claimed_at=utc_now_iso(),
        limit=limit,
    )


def resolve_processing_job(
    *,
    job_id: str,
    expected_worker_id: str | None,
    repository: ReportGenerationJobRepository,
) -> ReportGenerationJob:
    """처리 가능한 job 상태를 검증하고 processing job을 돌려준다."""

    job = repository.get_by_id(job_id)
    if job is None:
        raise ValueError(f"리포트 생성 job을 찾을 수 없습니다: {job_id}")
    if job.status == "completed":
        return job

    if expected_worker_id is not None:
        if job.status != "processing":
            raise ValueError(f"claim되지 않은 리포트 생성 job입니다: {job_id}")
        if job.claimed_by_worker_id != expected_worker_id:
            raise ValueError(f"다른 worker가 claim한 리포트 생성 job입니다: {job_id}")
        return job

    if job.status == "processing":
        return job

    return repository.update(
        job.mark_processing(
            started_at=utc_now_iso(),
        )
    )
