"""Note correction job repository 매핑 helper."""

from __future__ import annotations

from server.app.domain.models.note_correction_job import NoteCorrectionJob


def job_to_insert_row(job: NoteCorrectionJob) -> tuple[object, ...]:
    """INSERT용 job row를 만든다."""

    return (
        job.id,
        job.session_id,
        job.source_version,
        job.status,
        job.error_message,
        job.requested_by_user_id,
        job.claimed_by_worker_id,
        job.lease_expires_at,
        job.attempt_count,
        job.created_at,
        job.started_at,
        job.completed_at,
    )


def job_to_update_row(job: NoteCorrectionJob) -> tuple[object, ...]:
    """UPDATE용 job row를 만든다."""

    return (
        job.source_version,
        job.status,
        job.error_message,
        job.requested_by_user_id,
        job.claimed_by_worker_id,
        job.lease_expires_at,
        job.attempt_count,
        job.created_at,
        job.started_at,
        job.completed_at,
        job.id,
    )


def row_to_job(row) -> NoteCorrectionJob | None:
    """DB row를 NoteCorrectionJob으로 변환한다."""

    if row is None:
        return None
    return NoteCorrectionJob(
        id=row["id"],
        session_id=row["session_id"],
        source_version=int(row["source_version"] or 0),
        status=row["status"],
        error_message=row["error_message"],
        requested_by_user_id=row["requested_by_user_id"],
        claimed_by_worker_id=row["claimed_by_worker_id"],
        lease_expires_at=row["lease_expires_at"],
        attempt_count=int(row["attempt_count"] or 0),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )
