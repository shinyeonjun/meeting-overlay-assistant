"""세션 녹음 파일 조회 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.services.audio.io.session_recording import (
    find_session_recording_artifact,
    resolve_recording_reference,
)

router = APIRouter()


@router.get("/{session_id}/recording")
def get_session_recording(
    session_id: str,
    download: bool = Query(default=False),
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> FileResponse:
    """세션 원본 녹음 파일을 inline 재생용으로 반환한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    recording_path = resolve_recording_reference(
        artifact_id=session.recording_artifact_id,
    )
    if recording_path is None:
        recording_artifact = find_session_recording_artifact(session.id)
        recording_path = recording_artifact.file_path if recording_artifact is not None else None

    if recording_path is None or not recording_path.exists():
        raise HTTPException(status_code=404, detail="세션 녹음 파일을 찾을 수 없습니다.")

    return FileResponse(
        path=recording_path,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'{"attachment" if download else "inline"}; filename="{session.id}.wav"',
        },
    )
