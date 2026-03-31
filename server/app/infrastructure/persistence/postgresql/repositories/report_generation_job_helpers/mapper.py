"""Report generation job repository 매핑 helper."""

from __future__ import annotations

from server.app.domain.models.report_generation_job import ReportGenerationJob


def job_to_insert_row(job: ReportGenerationJob) -> tuple[object, ...]:
    """INSERT용 job row를 만든다."""

    return (
        job.id,
        job.session_id,
        job.status,
        job.recording_artifact_id,
        job.recording_path,
        job.transcript_path,
        job.markdown_report_id,
        job.pdf_report_id,
        job.error_message,
        job.requested_by_user_id,
        job.claimed_by_worker_id,
        job.lease_expires_at,
        job.attempt_count,
        job.created_at,
        job.started_at,
        job.completed_at,
    )


def job_to_update_row(job: ReportGenerationJob) -> tuple[object, ...]:
    """UPDATE용 job row를 만든다."""

    return (
        job.status,
        job.recording_artifact_id,
        job.recording_path,
        job.transcript_path,
        job.markdown_report_id,
        job.pdf_report_id,
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


def row_to_job(row) -> ReportGenerationJob | None:
    """DB row를 ReportGenerationJob으로 변환한다."""

    if row is None:
        return None
    return ReportGenerationJob(
        id=row["id"],
        session_id=row["session_id"],
        status=row["status"],
        recording_artifact_id=(
            row["recording_artifact_id"] if "recording_artifact_id" in row else None
        ),
        recording_path=row["recording_path"],
        transcript_path=row["transcript_path"],
        markdown_report_id=row["markdown_report_id"],
        pdf_report_id=row["pdf_report_id"],
        error_message=row["error_message"],
        requested_by_user_id=row["requested_by_user_id"],
        claimed_by_worker_id=row["claimed_by_worker_id"],
        lease_expires_at=row["lease_expires_at"],
        attempt_count=int(row["attempt_count"] or 0),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )
