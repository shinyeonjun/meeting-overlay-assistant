"""HTTP 계층에서 참여자 관련 query 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import get_participation_query_service
from server.app.api.http.routes.session.support import resolve_workspace_id
from server.app.api.http.schemas.participation import (
    SessionParticipationResponse,
    SessionParticipationSummaryResponse,
    SessionParticipantCandidateMatchResponse,
    SessionParticipantCandidateResponse,
    SessionParticipantResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


@router.get("/{session_id}/participants", response_model=SessionParticipationResponse)
def get_session_participation(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionParticipationResponse:
    """세션 참여자 상세와 연결 상태를 조회한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    workspace_id = resolve_workspace_id(auth_context)
    participation = get_participation_query_service().build_session_participation(
        session=session,
        workspace_id=workspace_id,
    )
    return SessionParticipationResponse(
        session_id=participation.session_id,
        participants=[
            SessionParticipantResponse(
                name=item.name,
                normalized_name=item.normalized_name,
                contact_id=item.contact_id,
                account_id=item.account_id,
                email=item.email,
                job_title=item.job_title,
                department=item.department,
                resolution_status=item.resolution_status,
            )
            for item in participation.participants
        ],
        participant_candidates=[
            SessionParticipantCandidateResponse(
                name=item.name,
                account_id=item.account_id,
                resolution_status=item.resolution_status,
                matched_contact_count=item.matched_contact_count,
                matched_contacts=[
                    SessionParticipantCandidateMatchResponse(
                        contact_id=match.contact_id,
                        account_id=match.account_id,
                        name=match.name,
                        email=match.email,
                        job_title=match.job_title,
                        department=match.department,
                    )
                    for match in item.matched_contacts
                ],
            )
            for item in participation.participant_candidates
        ],
        summary=SessionParticipationSummaryResponse(
            total_count=participation.summary.total_count,
            linked_count=participation.summary.linked_count,
            unmatched_count=participation.summary.unmatched_count,
            ambiguous_count=participation.summary.ambiguous_count,
            unresolved_count=participation.summary.unresolved_count,
            pending_followup_count=participation.summary.pending_followup_count,
            resolved_followup_count=participation.summary.resolved_followup_count,
        ),
    )
