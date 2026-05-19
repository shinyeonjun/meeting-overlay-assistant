"""회의록 파이프라인의 최종 상태를 계산한다."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from server.app.core.config import settings
from server.app.domain.models.note_correction_job import NoteCorrectionJob
from server.app.domain.models.report import Report
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.services.reports.report_models import FinalReportStatus, SessionReportSummary


def build_final_report_status(
    *,
    session_id: str,
    session_ended: bool,
    post_processing_status: str,
    post_processing_job: SessionPostProcessingJob | None,
    post_processing_error_message: str | None,
    canonical_transcript_version: int,
    note_correction_job: NoteCorrectionJob | None,
    latest_job: ReportGenerationJob | None,
    report_summary: SessionReportSummary,
    report_exists: Callable[[Report], bool],
) -> FinalReportStatus:
    """후처리부터 회의록 생성까지의 파이프라인 상태를 한 번에 계산한다."""

    latest_report = report_summary.latest_report
    has_usable_report = latest_report is not None and report_exists(latest_report)

    current_post_processing_job = (
        post_processing_job
        if post_processing_job is not None and post_processing_job.session_id == session_id
        else None
    )
    current_note_correction_job = (
        note_correction_job
        if note_correction_job is not None
        and note_correction_job.source_version == canonical_transcript_version
        else None
    )
    note_correction_job_status = (
        current_note_correction_job.status if current_note_correction_job is not None else None
    )
    note_correction_job_error_message = (
        current_note_correction_job.error_message
        if current_note_correction_job is not None
        else None
    )
    latest_job_status = latest_job.status if latest_job is not None else None
    latest_job_error_message = latest_job.error_message if latest_job is not None else None
    note_correction_stage_active = (
        settings.note_transcript_correction_enabled or current_note_correction_job is not None
    )

    stalled_status = _resolve_stalled_status(
        post_processing_status=post_processing_status,
        post_processing_job=current_post_processing_job,
        note_correction_stage_active=note_correction_stage_active,
        note_correction_job=current_note_correction_job,
        note_correction_job_status=note_correction_job_status,
        latest_job=latest_job,
        latest_job_status=latest_job_status,
    )
    if stalled_status is not None:
        status, pipeline_stage, warning_reason = stalled_status
    else:
        status, pipeline_stage = _resolve_pipeline_status(
            session_ended=session_ended,
            post_processing_status=post_processing_status,
            note_correction_job=(
                current_note_correction_job if note_correction_stage_active else None
            ),
            latest_job=latest_job,
            report_count=report_summary.report_count,
            has_usable_report=has_usable_report,
        )
        warning_reason = _resolve_report_warning_reason(
            has_usable_report=has_usable_report,
            latest_job=latest_job,
            post_processing_status=post_processing_status,
        )

    return _build_status_response(
        session_id=session_id,
        status=status,
        pipeline_stage=pipeline_stage,
        report_summary=report_summary,
        post_processing_status=post_processing_status,
        post_processing_error_message=post_processing_error_message,
        note_correction_job_status=note_correction_job_status,
        note_correction_job_error_message=note_correction_job_error_message,
        warning_reason=warning_reason,
        latest_job_status=latest_job_status,
        latest_job_error_message=latest_job_error_message,
    )


def _resolve_stalled_status(
    *,
    post_processing_status: str,
    post_processing_job: SessionPostProcessingJob | None,
    note_correction_stage_active: bool,
    note_correction_job: NoteCorrectionJob | None,
    note_correction_job_status: str | None,
    latest_job: ReportGenerationJob | None,
    latest_job_status: str | None,
) -> tuple[str, str, str] | None:
    if _is_stalled_job(
        status=post_processing_status,
        lease_expires_at=(
            post_processing_job.lease_expires_at
            if post_processing_job is not None
            else None
        ),
    ):
        return "failed", "post_processing", "post_processing_stalled"

    if note_correction_stage_active and _is_stalled_job(
        status=note_correction_job_status,
        lease_expires_at=(
            note_correction_job.lease_expires_at
            if note_correction_job is not None
            else None
        ),
    ):
        return "failed", "note_correction", "note_correction_stalled"

    if _is_stalled_job(
        status=latest_job_status,
        lease_expires_at=latest_job.lease_expires_at if latest_job is not None else None,
    ):
        return "failed", "report_generation", "report_generation_stalled"

    return None


def _resolve_pipeline_status(
    *,
    session_ended: bool,
    post_processing_status: str,
    note_correction_job: NoteCorrectionJob | None,
    latest_job: ReportGenerationJob | None,
    report_count: int,
    has_usable_report: bool,
) -> tuple[str, str]:
    normalized_post_processing_status = (
        post_processing_status.strip().lower() if post_processing_status else "not_started"
    )

    if not session_ended:
        return "pending", "live"

    if normalized_post_processing_status in {"not_started", "queued"}:
        return "pending", "post_processing"
    if _is_processing_status(normalized_post_processing_status):
        return "processing", "post_processing"
    if normalized_post_processing_status == "failed":
        return "failed", "post_processing"

    if note_correction_job is None:
        report_generation_status = _resolve_report_generation_status(
            latest_job=latest_job,
            has_usable_report=has_usable_report,
        )
        if report_generation_status is not None:
            return report_generation_status
        if has_usable_report:
            return "completed", "completed"
        if report_count > 0:
            return "pending", "report_generation"
        return "pending", "note_correction"
    if note_correction_job.status == "pending":
        return "pending", "note_correction"
    if note_correction_job.status == "processing":
        return "processing", "note_correction"
    if note_correction_job.status == "failed":
        return "failed", "note_correction"

    report_generation_status = _resolve_report_generation_status(
        latest_job=latest_job,
        has_usable_report=has_usable_report,
    )
    if report_generation_status is not None:
        return report_generation_status

    if has_usable_report:
        return "completed", "completed"

    return "pending", "report_generation"


def _resolve_report_generation_status(
    *,
    latest_job: ReportGenerationJob | None,
    has_usable_report: bool,
) -> tuple[str, str] | None:
    if latest_job is None:
        return None
    if latest_job.status == "pending":
        return "pending", "report_generation"
    if latest_job.status == "processing":
        return "processing", "report_generation"
    if latest_job.status == "failed":
        return "failed", "report_generation"
    if latest_job.status == "completed" and not has_usable_report:
        return "failed", "report_generation"
    return None


def _build_status_response(
    *,
    session_id: str,
    status: str,
    pipeline_stage: str,
    report_summary: SessionReportSummary,
    post_processing_status: str,
    post_processing_error_message: str | None,
    note_correction_job_status: str | None,
    note_correction_job_error_message: str | None,
    warning_reason: str | None,
    latest_job_status: str | None,
    latest_job_error_message: str | None,
) -> FinalReportStatus:
    latest_report = report_summary.latest_report
    return FinalReportStatus(
        session_id=session_id,
        status=status,
        pipeline_stage=pipeline_stage,
        report_count=report_summary.report_count,
        post_processing_status=post_processing_status,
        post_processing_error_message=post_processing_error_message,
        note_correction_job_status=note_correction_job_status,
        note_correction_job_error_message=note_correction_job_error_message,
        latest_report_id=latest_report.id if latest_report is not None else None,
        latest_report_type=latest_report.report_type if latest_report is not None else None,
        latest_generated_at=latest_report.generated_at if latest_report is not None else None,
        latest_file_artifact_id=latest_report.file_artifact_id if latest_report is not None else None,
        latest_file_path=latest_report.file_path if latest_report is not None else None,
        warning_reason=warning_reason,
        latest_job_status=latest_job_status,
        latest_job_error_message=latest_job_error_message,
    )


def _resolve_report_warning_reason(
    *,
    has_usable_report: bool,
    latest_job: ReportGenerationJob | None,
    post_processing_status: str,
) -> str | None:
    if not has_usable_report:
        return None

    if latest_job is not None and latest_job.status != "completed":
        return _resolve_warning_reason(latest_job.status)
    if latest_job is not None and latest_job.status == "completed" and latest_job.error_message:
        return "report_generation_fallback"
    if post_processing_status == "failed":
        return "latest_post_processing_failed"
    return None


def _resolve_warning_reason(latest_job_status: str) -> str | None:
    if latest_job_status == "failed":
        return "latest_regeneration_failed"
    if latest_job_status == "processing":
        return "latest_regeneration_processing"
    if latest_job_status == "pending":
        return "latest_regeneration_pending"
    return None


def _is_stalled_job(
    *,
    status: str | None,
    lease_expires_at: str | None,
) -> bool:
    if not _is_processing_status(status) or not lease_expires_at:
        return False

    try:
        lease_deadline = datetime.fromisoformat(lease_expires_at)
    except ValueError:
        return False

    if lease_deadline.tzinfo is None:
        lease_deadline = lease_deadline.replace(tzinfo=timezone.utc)
    return lease_deadline <= datetime.now(timezone.utc)


def _is_processing_status(status: str | None) -> bool:
    normalized = status.strip().lower() if status else ""
    return normalized == "processing" or normalized.startswith("processing_")
