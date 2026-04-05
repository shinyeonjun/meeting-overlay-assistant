"""세션 관리 라우터."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import (
    get_session_post_processing_job_service,
    get_session_service,
)
from server.app.api.http.routes.session.support import (
    resolve_workspace_id,
    to_session_response,
)
from server.app.api.http.schemas.meeting_session import (
    SessionResponse,
    SessionUpdateRequest,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.domain.shared.enums import SessionStatus
from server.app.services.audio.io.session_recording import (
    find_session_recording_artifact,
    resolve_recording_reference,
)

router = APIRouter()


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """세션 제목을 변경한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    try:
        updated_session = get_session_service().rename_session(session_id, request.title)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return to_session_response(
        updated_session,
        workspace_id=resolve_workspace_id(auth_context),
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> Response:
    """세션과 관련된 데이터를 삭제한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    try:
        get_session_service().delete_session(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/reprocess", response_model=SessionResponse)
def reprocess_session(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionResponse:
    """세션 노트 후처리를 다시 요청한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    if session.status == SessionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="진행 중인 회의는 노트를 다시 생성할 수 없습니다.",
        )

    recording_path = resolve_recording_reference(
        artifact_id=session.recording_artifact_id,
    )
    if recording_path is None:
        recording_artifact = find_session_recording_artifact(session.id)
        recording_path = recording_artifact.file_path if recording_artifact is not None else None

    if recording_path is None or not recording_path.exists():
        raise HTTPException(
            status_code=400,
            detail="다시 생성할 녹음 파일이 없습니다.",
        )

    get_session_post_processing_job_service().enqueue_for_session(
        session_id=session.id,
        requested_by_user_id=auth_context.user.id if auth_context is not None else None,
        dispatch=True,
    )
    refreshed = get_session_service().get_session(session.id) or session
    return to_session_response(
        refreshed,
        workspace_id=resolve_workspace_id(auth_context),
    )
