"""텍스트 입력 WebSocket 라우트."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from backend.app.api.http.dependencies import (
    get_session_service,
    get_text_input_pipeline_service,
)
from backend.app.api.http.routes.audio_ws import _stream_text


router = APIRouter(tags=["text"])


@router.websocket("/api/v1/ws/text/{session_id}")
async def text_input_stream(websocket: WebSocket, session_id: str) -> None:
    """텍스트 입력을 받아 발화와 이벤트를 생성한다."""

    session_service = get_session_service()
    session = session_service.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
        return

    input_source = websocket.query_params.get("input_source")
    if not input_source:
        input_source = "mic" if session.source.value == "mic_and_audio" else session.source.value

    session_service.mark_active_source(session_id, input_source)
    await _stream_text(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=get_text_input_pipeline_service(),
        input_source=input_source,
    )
