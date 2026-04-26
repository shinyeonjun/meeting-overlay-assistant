"""리포트 영역의 report models 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.models.report import Report
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.html_report_template import ReportDocumentV1
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)


@dataclass(frozen=True)
class BuiltMarkdownReport:
    """생성된 Markdown 리포트 결과."""

    report: Report
    content: str
    speaker_transcript: list[SpeakerTranscriptSegment]
    speaker_events: list[SpeakerAttributedEvent]
    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None


@dataclass(frozen=True)
class BuiltPdfReport:
    """생성된 PDF 리포트 결과."""

    report: Report
    source_markdown: str
    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None


@dataclass(frozen=True)
class FinalReportStatus:
    """최종 문서 생성 상태."""

    session_id: str
    status: str
    pipeline_stage: str
    report_count: int
    post_processing_status: str | None = None
    post_processing_error_message: str | None = None
    note_correction_job_status: str | None = None
    note_correction_job_error_message: str | None = None
    latest_report_id: str | None = None
    latest_report_type: str | None = None
    latest_generated_at: str | None = None
    latest_file_artifact_id: str | None = None
    latest_file_path: str | None = None
    warning_reason: str | None = None
    latest_job_status: str | None = None
    latest_job_error_message: str | None = None


@dataclass(frozen=True)
class SessionReportSummary:
    """세션별 최신 리포트와 누적 개수 요약."""

    session_id: str
    report_count: int
    latest_report: Report | None = None


@dataclass(frozen=True)
class ReportInsightResolution:
    """리포트 생성에 사용할 인사이트 집합과 출처."""

    events: list
    insight_source: str


@dataclass(frozen=True)
class PreparedReportContent:
    """Markdown/PDF가 공통으로 사용하는 계산 결과."""

    markdown_content: str
    report_document: ReportDocumentV1
    html_content: str
    speaker_transcript: list[SpeakerTranscriptSegment]
    speaker_events: list[SpeakerAttributedEvent]
    insight_source: str
    transcript_markdown: str | None = None
    analysis_snapshot: dict[str, object] | None = None
    speaker_processing_error: str | None = None


@dataclass(frozen=True)
class SavedReportArtifacts:
    """리포트 생성 중 저장한 중간 산출물 경로."""

    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None
