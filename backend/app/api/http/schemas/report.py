"""리포트 응답 스키마."""

from pydantic import BaseModel


class SpeakerTranscriptItemResponse(BaseModel):
    """화자별 전사 응답 항목."""

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
    file_path: str
    insight_source: str
    content: str
    speaker_transcript: list[SpeakerTranscriptItemResponse]
    speaker_events: list[SpeakerEventItemResponse]


class ReportItemResponse(BaseModel):
    """리포트 메타데이터 응답 항목."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_path: str
    insight_source: str
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
    file_path: str
    insight_source: str
    generated_at: str
    content: str | None


class PdfReportResponse(BaseModel):
    """PDF 리포트 생성 응답."""

    id: str
    session_id: str
    report_type: str
    version: int
    file_path: str
    insight_source: str
    source_markdown: str


class RegeneratedReportItemResponse(BaseModel):
    """재생성된 리포트 응답 항목."""

    id: str
    report_type: str
    version: int
    file_path: str
    insight_source: str


class RegenerateReportsResponse(BaseModel):
    """리포트 재생성 응답."""

    session_id: str
    items: list[RegeneratedReportItemResponse]


class FinalReportStatusResponse(BaseModel):
    """최종 문서 생성 상태 응답."""

    session_id: str
    status: str
    report_count: int
    latest_report_id: str | None = None
    latest_report_type: str | None = None
    latest_generated_at: str | None = None
    latest_file_path: str | None = None
