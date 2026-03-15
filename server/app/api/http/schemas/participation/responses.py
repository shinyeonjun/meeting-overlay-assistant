"""참여자 응답 스키마."""

from pydantic import BaseModel, Field


class SessionParticipantResponse(BaseModel):
    """세션 참여자와 contact 연결 정보."""

    name: str
    normalized_name: str | None = None
    contact_id: str | None = None
    account_id: str | None = None
    email: str | None = None
    job_title: str | None = None
    department: str | None = None
    resolution_status: str = "unmatched"


class SessionParticipantCandidateMatchResponse(BaseModel):
    """ambiguous 참여자에 대한 기존 contact 후보 응답."""

    contact_id: str
    account_id: str | None = None
    name: str
    email: str | None = None
    job_title: str | None = None
    department: str | None = None


class SessionParticipantCandidateResponse(BaseModel):
    """세션 참여자 후보 응답."""

    name: str
    account_id: str | None = None
    resolution_status: str
    matched_contact_count: int = 0
    matched_contacts: list[SessionParticipantCandidateMatchResponse] = Field(default_factory=list)


class ParticipantFollowupResponse(BaseModel):
    """참여자 후속 작업 응답."""

    id: str
    session_id: str
    participant_order: int
    participant_name: str
    resolution_status: str
    followup_status: str
    matched_contact_count: int = 0
    contact_id: str | None = None
    account_id: str | None = None
    created_at: str
    updated_at: str
    resolved_at: str | None = None
    resolved_by_user_id: str | None = None


class ParticipantFollowupListResponse(BaseModel):
    """참여자 후속 작업 목록 응답."""

    items: list[ParticipantFollowupResponse] = Field(default_factory=list)


class SessionParticipationSummaryResponse(BaseModel):
    """세션 참여자 연결 요약 응답."""

    total_count: int = 0
    linked_count: int = 0
    unmatched_count: int = 0
    ambiguous_count: int = 0
    unresolved_count: int = 0
    pending_followup_count: int = 0
    resolved_followup_count: int = 0


class SessionParticipationResponse(BaseModel):
    """세션 참여자 상세 응답."""

    session_id: str
    participants: list[SessionParticipantResponse] = Field(default_factory=list)
    participant_candidates: list[SessionParticipantCandidateResponse] = Field(default_factory=list)
    summary: SessionParticipationSummaryResponse
