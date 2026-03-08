"""세션 API 스키마."""

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    """세션 생성 요청."""

    title: str = Field(..., min_length=1)
    mode: str = Field(default="meeting")
    source: str = Field(default="system_audio")


class SessionResponse(BaseModel):
    """세션 응답."""

    id: str
    title: str
    mode: str
    source: str
    status: str
    started_at: str
    ended_at: str | None = None
    primary_input_source: str | None = None
    actual_active_sources: list[str] = Field(default_factory=list)
