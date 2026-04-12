"""세션 생성/시작/종료/목록 라우트."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from server.app.api.http.access_control import (
    get_accessible_session_or_raise,
    resolve_scope_owner_id,
)
from server.app.api.http.dependencies import (
    get_context_resolution_service,
    get_post_meeting_pipeline_service,
    get_session_service,
)
from server.app.api.http.routes.session.support import (
    resolve_workspace_id,
    to_session_response,
)
from server.app.api.http.schemas.meeting_session import (
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.domain.shared.enums import AudioSource, SessionMode

router = APIRouter()


@router.get("/", response_model=SessionListResponse)
def list_sessions(
    scope: str = "mine",
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    limit: int = 20,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionListResponse:
    """최신 세션 목록을 조회한다."""

    owner_filter = resolve_scope_owner_id(scope, auth_context)
    workspace_id = resolve_workspace_id(auth_context)
    items = get_session_service().list_sessions(
        created_by_user_id=owner_filter,
        account_id=account_id,
        contact_id=contact_id,
        context_thread_id=context_thread_id,
        limit=max(1, min(limit, 100)),
    )
    return SessionListResponse(
        items=[to_session_response(item, workspace_id=workspace_id) for item in items]
    )


@router.post("/", response_model=SessionResponse)
def create_session(
    request: SessionCreateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """초기 draft 세션을 생성한다."""

    session_service = get_session_service()
    workspace_id = resolve_workspace_id(auth_context)
    try:
        resolved_context = get_context_resolution_service().resolve_session_context(
            workspace_id=workspace_id,
            account_id=request.account_id,
            contact_id=request.contact_id,
            context_thread_id=request.context_thread_id,
        )
        session = session_service.create_session_draft(
            title=request.title,
            mode=SessionMode(request.mode),
            source=AudioSource(request.primary_input_source),
            created_by_user_id=auth_context.user.id if auth_context is not None else None,
            account_id=resolved_context.account_id,
            contact_id=resolved_context.contact_id,
            context_thread_id=resolved_context.context_thread_id,
            workspace_id=workspace_id,
            participants=request.participants,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return to_session_response(session, workspace_id=workspace_id)


@router.post("/{session_id}/start", response_model=SessionResponse)
def start_session(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """draft 세션을 시작한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    workspace_id = resolve_workspace_id(auth_context)
    try:
        session = get_session_service().start_session(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return to_session_response(session, workspace_id=workspace_id)


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """세션을 종료한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    post_meeting_pipeline_service = get_post_meeting_pipeline_service()
    try:
        result = post_meeting_pipeline_service.finalize_session(
            session_id,
            workspace_id=resolve_workspace_id(auth_context),
            resolved_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    if (
        result.report_generation_job is not None
        and result.should_process_report_job
    ):
        background_tasks.add_task(
            post_meeting_pipeline_service.process_report_generation_job,
            result.report_generation_job.id,
        )

    return to_session_response(
        result.session,
        workspace_id=resolve_workspace_id(auth_context),
    )
