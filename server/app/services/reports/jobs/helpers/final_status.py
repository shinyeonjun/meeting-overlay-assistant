"""리포트 generation 최종 상태 조립 helper."""

from __future__ import annotations

from collections.abc import Callable

from server.app.domain.models.report import Report
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.services.reports.report_models import FinalReportStatus, SessionReportSummary


def build_final_report_status(
    *,
    session_id: str,
    session_ended: bool,
    latest_job: ReportGenerationJob | None,
    report_summary: SessionReportSummary,
    report_exists: Callable[[Report], bool],
) -> FinalReportStatus:
    """최신 job 상태와 usable report 존재 여부를 함께 반영한다."""

    latest_report = report_summary.latest_report
    has_usable_report = latest_report is not None and report_exists(latest_report)

    warning_reason = None
    latest_job_status = latest_job.status if latest_job is not None else None
    latest_job_error_message = latest_job.error_message if latest_job is not None else None

    if latest_job is None:
        status = _resolve_status_without_job(
            session_ended=session_ended,
            latest_report=latest_report,
            report_exists=report_exists,
        )
    elif latest_job.status == "completed":
        status = "completed" if has_usable_report else "failed"
    elif has_usable_report:
        status = "completed"
        warning_reason = _resolve_warning_reason(latest_job.status)
    else:
        status = latest_job.status

    return _build_status_response(
        session_id=session_id,
        status=status,
        report_summary=report_summary,
        warning_reason=warning_reason,
        latest_job_status=latest_job_status,
        latest_job_error_message=latest_job_error_message,
    )


def _resolve_status_without_job(
    *,
    session_ended: bool,
    latest_report: Report | None,
    report_exists: Callable[[Report], bool],
) -> str:
    if latest_report is None:
        return "ready" if session_ended else "pending"
    return "completed" if report_exists(latest_report) else "failed"


def _build_status_response(
    *,
    session_id: str,
    status: str,
    report_summary: SessionReportSummary,
    warning_reason: str | None,
    latest_job_status: str | None,
    latest_job_error_message: str | None,
) -> FinalReportStatus:
    latest_report = report_summary.latest_report
    return FinalReportStatus(
        session_id=session_id,
        status=status,
        report_count=report_summary.report_count,
        latest_report_id=latest_report.id if latest_report is not None else None,
        latest_report_type=latest_report.report_type if latest_report is not None else None,
        latest_generated_at=latest_report.generated_at if latest_report is not None else None,
        latest_file_artifact_id=latest_report.file_artifact_id if latest_report is not None else None,
        latest_file_path=latest_report.file_path if latest_report is not None else None,
        warning_reason=warning_reason,
        latest_job_status=latest_job_status,
        latest_job_error_message=latest_job_error_message,
    )


def _resolve_warning_reason(latest_job_status: str) -> str | None:
    if latest_job_status == "failed":
        return "latest_regeneration_failed"
    if latest_job_status == "processing":
        return "latest_regeneration_processing"
    if latest_job_status == "pending":
        return "latest_regeneration_pending"
    return None
