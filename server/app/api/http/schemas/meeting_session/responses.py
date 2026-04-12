"""세션 응답 스키마."""

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
    primary_input_source: str
    actual_active_sources: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    participant_summary: SessionParticipationSummaryResponse


class SessionListResponse(BaseModel):
    """세션 목록 응답."""

    items: list[SessionResponse]
