"""final status helper 회귀 테스트."""

from server.app.domain.models.report import Report
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
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
        post_processing_job=None,
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


def test_processing_stage_status_is_treated_as_post_processing():
    status = build_final_report_status(
        session_id="session-1",
        session_ended=True,
        post_processing_status="processing_transcribe",
        post_processing_job=None,
        post_processing_error_message=None,
        canonical_transcript_version=0,
        note_correction_job=None,
        latest_job=None,
        report_summary=SessionReportSummary(
            session_id="session-1",
            report_count=0,
            latest_report=None,
        ),
        report_exists=lambda report: False,
    )

    assert status.status == "processing"
    assert status.pipeline_stage == "post_processing"


def test_processing_stage_status_can_be_marked_as_stalled():
    job = SessionPostProcessingJob.create_pending(
        session_id="session-1",
        recording_artifact_id=None,
        recording_path=None,
    ).mark_processing(
        lease_expires_at="2000-01-01T00:00:00+00:00",
    )

    status = build_final_report_status(
        session_id="session-1",
        session_ended=True,
        post_processing_status="processing_transcribe",
        post_processing_job=job,
        post_processing_error_message=None,
        canonical_transcript_version=0,
        note_correction_job=None,
        latest_job=None,
        report_summary=SessionReportSummary(
            session_id="session-1",
            report_count=0,
            latest_report=None,
        ),
        report_exists=lambda report: False,
    )

    assert status.status == "failed"
    assert status.pipeline_stage == "post_processing"
    assert status.warning_reason == "post_processing_stalled"
