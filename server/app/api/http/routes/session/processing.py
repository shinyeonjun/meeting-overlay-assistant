"""세션 후처리 상태 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import get_session_post_processing_job_service
from server.app.api.http.schemas.meeting_session import SessionProcessingResponse
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


@router.get("/{session_id}/processing", response_model=SessionProcessingResponse)
def get_session_processing_status(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionProcessingResponse:
    """세션 후처리 상태를 조회한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    latest_job = get_session_post_processing_job_service().get_latest_job(session_id)
    return SessionProcessingResponse(
        session_id=session.id,
        status=session.post_processing_status,
        error_message=session.post_processing_error_message,
        recording_artifact_id=session.recording_artifact_id,
        requested_at=session.post_processing_requested_at,
        started_at=session.post_processing_started_at,
        completed_at=session.post_processing_completed_at,
        canonical_transcript_version=session.canonical_transcript_version,
        canonical_events_version=session.canonical_events_version,
        latest_job_id=latest_job.id if latest_job is not None else None,
        latest_job_status=latest_job.status if latest_job is not None else None,
        latest_job_error_message=(
            latest_job.error_message if latest_job is not None else None
        ),
    )
