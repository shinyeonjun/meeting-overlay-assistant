"""HTTP 계층에서 공통 관련 report 구성을 담당한다."""
from pydantic import BaseModel


class SpeakerTranscriptItemResponse(BaseModel):
    """화자 전사 응답 항목."""

    speaker_label: str
    start_ms: int
    end_ms: int
    text: str
    confidence: float


class SpeakerEventItemResponse(BaseModel):
    """화자-이벤트 연결 응답 항목."""

    speaker_label: str
    event_type: str
    title: str
    state: str


class MarkdownReportResponse(BaseModel):
    """Markdown 리포트 생성 응답."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_artifact_id: str | None = None
    file_path: str
    insight_source: str
    generated_by_user_id: str | None = None
    content: str
    speaker_transcript: list[SpeakerTranscriptItemResponse]
    speaker_events: list[SpeakerEventItemResponse]
    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None
    document_path: str | None = None


class ReportItemResponse(BaseModel):
    """리포트 메타데이터 응답 항목."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_artifact_id: str | None = None
    file_path: str
    insight_source: str
    generated_by_user_id: str | None = None
    generated_at: str


class ReportListResponse(BaseModel):
    """세션 리포트 목록 응답."""

    items: list[ReportItemResponse]


class LatestReportResponse(BaseModel):
    """최신 리포트 조회 응답."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_artifact_id: str | None = None
    file_path: str
    insight_source: str
    generated_by_user_id: str | None = None
    generated_at: str
    content: str | None


class PdfReportResponse(BaseModel):
    """PDF 리포트 생성 응답."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_artifact_id: str | None = None
    file_path: str
    insight_source: str
    generated_by_user_id: str | None = None
    source_markdown: str
    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None
    document_path: str | None = None


class RegeneratedReportItemResponse(BaseModel):
    """재생성한 리포트 응답 항목."""

    id: str
    report_type: str
    version: int
    file_artifact_id: str | None = None
    file_path: str
    insight_source: str
    generated_by_user_id: str | None = None


class RegenerateReportsResponse(BaseModel):
    """리포트 재생성 응답."""

    session_id: str
    items: list[RegeneratedReportItemResponse]


class FinalReportStatusResponse(BaseModel):
    """최종 문서 생성 상태 응답."""

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


class ReportGenerationJobResponse(BaseModel):
    """리포트 생성 job 상태 응답."""

    id: str
    session_id: str
    status: str
    recording_artifact_id: str | None = None
    recording_path: str | None = None
    transcript_path: str | None = None
    markdown_report_id: str | None = None
    pdf_report_id: str | None = None
    error_message: str | None = None
    requested_by_user_id: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class ReportShareCreateRequest(BaseModel):
    """리포트 공유 생성 요청."""

    shared_with_login_id: str
    note: str | None = None


class ReportShareResponse(BaseModel):
    """리포트 공유 응답."""

    id: str
    report_id: str
    shared_by_user_id: str
    shared_by_login_id: str
    shared_by_display_name: str
    shared_with_user_id: str
    shared_with_login_id: str
    shared_with_display_name: str
    permission: str
    note: str | None = None
    created_at: str


class ReportShareListResponse(BaseModel):
    """리포트 공유 목록 응답."""

    items: list[ReportShareResponse]


class ReportShareInboxItemResponse(BaseModel):
    """공유받은 리포트 목록 응답 항목."""

    share_id: str
    report_id: str
    session_id: str
    report_type: str
    version: int
    file_artifact_id: str | None = None
    file_path: str
    file_name: str
    insight_source: str
    generated_by_user_id: str | None = None
    generated_at: str
    shared_by_user_id: str
    shared_by_login_id: str
    shared_by_display_name: str
    permission: str
    note: str | None = None
    shared_at: str


class ReportShareInboxListResponse(BaseModel):
    """공유받은 리포트 목록 응답."""

    items: list[ReportShareInboxItemResponse]
