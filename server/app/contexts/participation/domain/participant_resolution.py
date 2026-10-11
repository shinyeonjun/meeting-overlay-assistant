"""참여자 contact 해석 모델."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionParticipantCandidate:
    """contact로 승격 가능성이 있는 세션 참여자 후보."""

    name: str
    account_id: str | None = None
    resolution_status: str = "unmatched"
    matched_contact_count: int = 0
    matched_contacts: tuple["SessionParticipantCandidateMatch", ...] = ()


@dataclass(frozen=True)
class SessionParticipantCandidateMatch:
    """ambiguous 참여자에 대해 고를 수 있는 contact 후보."""

    contact_id: str
    account_id: str | None = None
    name: str = ""
    email: str | None = None
    job_title: str | None = None
    department: str | None = None
