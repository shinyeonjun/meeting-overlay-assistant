"""오디오/텍스트 입력 WebSocket 라우트."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.api.http.dependencies import (
    get_audio_pipeline_service_for_source,
    get_session_service,
)
from backend.app.api.http.serializers.audio import build_stream_error_payload, build_stream_payload


logger = logging.getLogger(__name__)
router = APIRouter(tags=["audio"])


@router.websocket("/api/v1/ws/audio/{session_id}")
async def audio_stream(websocket: WebSocket, session_id: str) -> None:
    """PCM 오디오를 받아 발화/이벤트를 생성한다."""
    session_service = get_session_service()
    session = session_service.get_session(session_id)
    if session is None:
        await websocket.close(code=4404, reason="세션을 찾을 수 없습니다.")
        return

    logger.info(
        "오디오 WebSocket 연결 시작: session_id=%s source=%s",
        session_id,
        session.source.value,
    )
    input_source = websocket.query_params.get("input_source") or session.source.value
    session_service.mark_active_source(session_id, input_source)
    await _stream_bytes(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=get_audio_pipeline_service_for_source(session.source.value),
        input_source=input_source,
    )


async def _stream_bytes(websocket: WebSocket, session_id: str, pipeline_service, input_source: str | None) -> None:
    await _stream_loop(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=pipeline_service,
        receive_message=websocket.receive_bytes,
        to_chunk=lambda message: message,
        stream_name="오디오",
        close_reason="audio pipeline error",
        log_chunk_receive=True,
        input_source=input_source,
    )


async def _stream_text(websocket: WebSocket, session_id: str, pipeline_service, input_source: str | None) -> None:
    await _stream_loop(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=pipeline_service,
        receive_message=websocket.receive_text,
        to_chunk=lambda message: message.encode("utf-8"),
        stream_name="텍스트 입력",
        close_reason="text input pipeline error",
        log_chunk_receive=False,
        input_source=input_source,
    )


async def _stream_loop(
    *,
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    receive_message: Callable[[], Awaitable[bytes | str]],
    to_chunk: Callable[[bytes | str], bytes],
    stream_name: str,
    close_reason: str,
    log_chunk_receive: bool,
    input_source: str | None,
) -> None:
    await websocket.accept()

    try:
        while True:
            message = await receive_message()
            chunk = to_chunk(message)
            if log_chunk_receive:
                logger.debug(
                    "%s WebSocket 청크 수신: session_id=%s chunk_bytes=%d",
                    stream_name,
                    session_id,
                    len(chunk),
                )
            utterances, events = await asyncio.to_thread(
                pipeline_service.process_chunk,
                session_id,
                chunk,
                input_source,
            )
            if utterances or events:
                logger.info(
                    "%s WebSocket payload 전송: session_id=%s input_source=%s utterances=%d events=%d",
                    stream_name,
                    session_id,
                    input_source,
                    len(utterances),
                    len(events),
                )
            if utterances or events:
                await websocket.send_json(
                    build_stream_payload(
                        session_id,
                        utterances,
                        events,
                        input_source=input_source,
                    )
                )
    except WebSocketDisconnect:
        logger.info("%s WebSocket 연결 종료: session_id=%s", stream_name, session_id)
    except Exception as error:
        logger.exception("%s WebSocket 처리 실패: session_id=%s", stream_name, session_id)
        await websocket.send_json(build_stream_error_payload(session_id, str(error)))
        await websocket.close(code=1011, reason=close_reason)
    finally:
        _reset_pipeline_stream(pipeline_service)


def _reset_pipeline_stream(pipeline_service) -> None:
    speech_to_text_service = getattr(pipeline_service, "_speech_to_text_service", None)
    reset_stream = getattr(speech_to_text_service, "reset_stream", None)
    if callable(reset_stream):
        reset_stream()
