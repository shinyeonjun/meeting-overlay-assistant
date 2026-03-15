"""텍스트 입력 WebSocket 라우터."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from server.app.api.http.access_control import can_access_session
from server.app.api.http.dependencies import (
    get_session_service,
    get_text_input_pipeline_service,
)
from server.app.api.http.routes.audio_ws import _stream_text
from server.app.api.http.security import authenticate_websocket_if_required
from server.app.core.config import settings
from server.app.domain.shared.enums import SessionStatus


router = APIRouter(tags=["text"])


@router.websocket("/api/v1/ws/text/{session_id}")
async def text_input_stream(websocket: WebSocket, session_id: str) -> None:
    """텍스트 입력을 받아 발화와 이벤트를 생성한다."""

    auth_context = await authenticate_websocket_if_required(websocket)
    if settings.auth_enabled and auth_context is None:
        return

    session_service = get_session_service()
    session = session_service.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
        return
    if session.status != SessionStatus.RUNNING:
        await websocket.close(code=4409, reason="진행 중인 세션만 실시간 연결을 허용합니다.")
        return
    if not can_access_session(session, auth_context):
        await websocket.close(code=4403, reason="해당 세션에 접근할 권한이 없습니다.")
        return

    input_source = websocket.query_params.get("input_source")
    if not input_source:
        input_source = (
            "mic"
            if session.primary_input_source == "mic_and_audio"
            else session.primary_input_source
        )

    session_service.mark_active_source(session_id, input_source)
    await _stream_text(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=get_text_input_pipeline_service(),
        input_source=input_source,
    )
