"""오디오 입력 실시간 처리용 WebSocket 라우트."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from server.app.api.http.routes.websocket_streaming import (
    stream_bytes,
    stream_text,
)
from server.app.api.http.routes.websocket_streaming_helpers import (
    prepare_audio_websocket_connection,
)

router = APIRouter(tags=["audio"])


@router.websocket("/api/v1/ws/audio/{session_id}")
async def audio_stream(websocket: WebSocket, session_id: str) -> None:
    """PCM 오디오 스트림을 받아 실시간 전사 파이프라인으로 전달한다."""

    prepared = await prepare_audio_websocket_connection(
        websocket=websocket,
        session_id=session_id,
    )
    if prepared is None:
        return

    await _stream_bytes(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=prepared.pipeline_service,
        input_source=prepared.input_source,
    )


async def _stream_bytes(
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    input_source: str | None,
) -> None:
    """오디오 바이트 스트림 helper를 호환용 이름으로 유지한다."""

    await stream_bytes(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=pipeline_service,
        input_source=input_source,
    )


async def _stream_text(
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    input_source: str | None,
) -> None:
    """텍스트 스트림 helper를 호환용 이름으로 유지한다."""

    await stream_text(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=pipeline_service,
        input_source=input_source,
    )
