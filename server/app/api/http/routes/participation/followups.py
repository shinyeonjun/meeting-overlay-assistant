"""HTTP 계층에서 참여자 관련 followups 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import get_participant_followup_service
from server.app.api.http.schemas.participation import (
    ParticipantFollowupListResponse,
    ParticipantFollowupResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


@router.get("/{session_id}/participants/followups", response_model=ParticipantFollowupListResponse)
def list_session_participant_followups(
    session_id: str,
    followup_status: str | None = None,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ParticipantFollowupListResponse:
    """세션의 참여자 후속 작업 목록을 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    items = get_participant_followup_service().list_followups(
        session_id=session_id,
        followup_status=followup_status,
    )
    return ParticipantFollowupListResponse(
        items=[
            ParticipantFollowupResponse(
                id=item.id,
                session_id=item.session_id,
                participant_order=item.participant_order,
                participant_name=item.participant_name,
                resolution_status=item.resolution_status,
                followup_status=item.followup_status,
                matched_contact_count=item.matched_contact_count,
                contact_id=item.contact_id,
                account_id=item.account_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                resolved_at=item.resolved_at,
                resolved_by_user_id=item.resolved_by_user_id,
            )
            for item in items
        ]
    )
