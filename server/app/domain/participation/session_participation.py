"""세션 참여자 조회 모델."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.participation.participant_resolution import SessionParticipantCandidate
from server.app.domain.participation.session_participant import SessionParticipant


@dataclass(frozen=True)
class SessionParticipationSummary:
    """세션 참여자 연결 요약."""

    total_count: int
    linked_count: int
    unmatched_count: int
    ambiguous_count: int
    unresolved_count: int
    pending_followup_count: int
    resolved_followup_count: int


@dataclass(frozen=True)
class SessionParticipationView:
    """세션 참여자 상세 조회 결과."""

    session_id: str
    participants: tuple[SessionParticipant, ...]
    participant_candidates: tuple[SessionParticipantCandidate, ...]
    summary: SessionParticipationSummary
