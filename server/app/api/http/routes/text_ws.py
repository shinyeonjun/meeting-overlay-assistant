"""HTTP 계층에서 공통 관련 text ws 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket

from server.app.api.http.routes.audio_ws import _stream_text
from server.app.api.http.routes.websocket_streaming_helpers import (
    prepare_text_websocket_connection,
)

router = APIRouter(tags=["text"])


@router.websocket("/api/v1/ws/text/{session_id}")
async def text_input_stream(websocket: WebSocket, session_id: str) -> None:
    """텍스트 입력을 받아 발화와 이벤트를 생성한다."""

    prepared = await prepare_text_websocket_connection(
        websocket=websocket,
        session_id=session_id,
    )
    if prepared is None:
        return

    await _stream_text(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=prepared.pipeline_service,
        input_source=prepared.input_source,
    )
