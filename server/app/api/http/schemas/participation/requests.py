"""HTTP 계층에서 참여자 관련 requests 구성을 담당한다."""
from pydantic import BaseModel, Field


class SessionParticipantContactCreateRequest(BaseModel):
    """세션 참여자를 contact로 승격하기 위한 요청."""

    participant_name: str = Field(..., min_length=1)
    account_id: str | None = None
    email: str | None = None
    job_title: str | None = None
    department: str | None = None
    notes: str | None = None


class SessionParticipantContactLinkRequest(BaseModel):
    """세션 참여자를 기존 contact에 연결하기 위한 요청."""

    participant_name: str = Field(..., min_length=1)
    contact_id: str = Field(..., min_length=1)
