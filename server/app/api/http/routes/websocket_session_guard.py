"""WebSocket 세션 접근 검증 helper."""

from __future__ import annotations

from fastapi import WebSocket

from server.app.api.http.access_control import can_access_session
from server.app.domain.shared.enums import SessionStatus


async def validate_running_session_access(
    *,
    websocket: WebSocket,
    session_service,
    session_id: str,
    auth_context,
):
    """실시간 WebSocket 접근이 가능한 세션인지 검증한다."""

    session = session_service.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
        return None
    if session.status != SessionStatus.RUNNING:
        await websocket.close(code=4409, reason="진행 중인 세션만 실시간 연결을 허용합니다.")
        return None
    if not can_access_session(session, auth_context):
        await websocket.close(code=4403, reason="해당 세션에 접근할 권한이 없습니다.")
        return None
    return session
