"""final status helper 회귀 테스트."""

from server.app.domain.models.report import Report
from server.app.services.reports.jobs.helpers.final_status import (
    build_final_report_status,
)
from server.app.services.reports.report_models import SessionReportSummary


def test_legacy_report_only_session_is_treated_as_completed():
    latest_report = Report.create(
        session_id="session-1",
        report_type="markdown",
        version=1,
        file_path="reports/session-1.md",
        insight_source="legacy",
    )

    status = build_final_report_status(
        session_id="session-1",
        session_ended=True,
        post_processing_status="completed",
        post_processing_error_message=None,
        canonical_transcript_version=1,
        note_correction_job=None,
        latest_job=None,
        report_summary=SessionReportSummary(
            session_id="session-1",
            report_count=1,
            latest_report=latest_report,
        ),
        report_exists=lambda report: report.id == latest_report.id,
    )

    assert status.status == "completed"
    assert status.pipeline_stage == "completed"
