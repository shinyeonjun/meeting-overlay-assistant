"""HTTP 계층에서 공통 관련 responses 구성을 담당한다."""
from pydantic import BaseModel, Field

from server.app.api.http.schemas.participation.responses import (
    SessionParticipationSummaryResponse,
)


class SessionResponse(BaseModel):
    """세션 응답."""

    id: str
    title: str
    mode: str
    status: str
    started_at: str
    created_by_user_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    ended_at: str | None = None
    recovery_required: bool = False
    recovery_reason: str | None = None
    recovery_detected_at: str | None = None
    recording_artifact_id: str | None = None
    recording_available: bool = False
    post_processing_status: str = "not_started"
    post_processing_error_message: str | None = None
    post_processing_requested_at: str | None = None
    post_processing_started_at: str | None = None
    post_processing_completed_at: str | None = None
    canonical_transcript_version: int = 0
    canonical_events_version: int = 0
    primary_input_source: str
    actual_active_sources: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    participant_summary: SessionParticipationSummaryResponse


class SessionListResponse(BaseModel):
    """세션 목록 응답."""

    items: list[SessionResponse]


class SessionProcessingResponse(BaseModel):
    """세션 후처리 상태 응답."""

    session_id: str
    status: str
    error_message: str | None = None
    recording_artifact_id: str | None = None
    requested_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    canonical_transcript_version: int = 0
    canonical_events_version: int = 0
    latest_job_id: str | None = None
    latest_job_status: str | None = None
    latest_job_error_message: str | None = None


class SessionTranscriptItemResponse(BaseModel):
    """세션 transcript 타임라인 항목."""

    id: str
    seq_num: int
    speaker_label: str | None = None
    start_ms: int
    end_ms: int
    text: str
    raw_text: str
    is_corrected: bool = False
    confidence: float
    input_source: str | None = None
    transcript_source: str = "post_processed"
    processing_job_id: str | None = None


class SessionTranscriptResponse(BaseModel):
    """세션 canonical transcript 응답."""

    session_id: str
    status: str
    canonical_transcript_version: int = 0
    items: list[SessionTranscriptItemResponse]
