"""HTTP 계층에서 참여자 관련 resolution 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import (
    get_context_catalog_service,
    get_participant_followup_service,
    get_session_service,
)
from server.app.api.http.routes.session.support import (
    resolve_workspace_id,
    to_session_response,
)
from server.app.api.http.schemas.meeting_session import SessionResponse
from server.app.api.http.schemas.participation import (
    SessionParticipantContactCreateRequest,
    SessionParticipantContactLinkRequest,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


@router.post("/{session_id}/participants/contacts", response_model=SessionResponse)
def create_contact_from_session_participant(
    session_id: str,
    request: SessionParticipantContactCreateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """세션 참여자를 contact로 승격하고 세션에 연결한다."""

    workspace_id = resolve_workspace_id(auth_context)
    session = get_accessible_session_or_raise(session_id, auth_context)
    candidate = get_session_service().get_participant_candidate(
        session=session,
        workspace_id=workspace_id,
        participant_name=request.participant_name,
    )
    if candidate is None:
        raise HTTPException(status_code=400, detail="contact 후보가 아닌 참여자입니다.")
    if candidate.resolution_status != "unmatched":
        raise HTTPException(
            status_code=400,
            detail="동명이인 contact가 여러 명 있어 자동 승격할 수 없습니다.",
        )

    target_account_id = request.account_id or candidate.account_id
    try:
        contact = get_context_catalog_service().create_contact(
            workspace_id=workspace_id,
            account_id=target_account_id,
            name=candidate.name,
            email=request.email,
            job_title=request.job_title,
            department=request.department,
            notes=request.notes,
            created_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
        updated_session = get_session_service().link_participant_contact(
            session_id=session_id,
            participant_name=candidate.name,
            contact_id=contact.id,
            account_id=contact.account_id or target_account_id,
            email=contact.email,
            job_title=contact.job_title,
            department=contact.department,
        )
        get_participant_followup_service().sync_followups_for_session(
            session=updated_session,
            workspace_id=workspace_id,
            resolved_by_user_id=auth_context.user.id if auth_context is not None else None,
            create_missing=False,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return to_session_response(updated_session, workspace_id=workspace_id)


@router.post("/{session_id}/participants/links", response_model=SessionResponse)
def link_existing_contact_to_session_participant(
    session_id: str,
    request: SessionParticipantContactLinkRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """동명이인 참여자를 기존 contact에 연결한다."""

    workspace_id = resolve_workspace_id(auth_context)
    get_accessible_session_or_raise(session_id, auth_context)
    try:
        updated_session = get_session_service().resolve_ambiguous_participant_contact(
            session_id=session_id,
            workspace_id=workspace_id,
            participant_name=request.participant_name,
            contact_id=request.contact_id,
        )
        get_participant_followup_service().sync_followups_for_session(
            session=updated_session,
            workspace_id=workspace_id,
            resolved_by_user_id=auth_context.user.id if auth_context is not None else None,
            create_missing=False,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return to_session_response(updated_session, workspace_id=workspace_id)
