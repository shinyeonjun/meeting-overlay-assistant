"""HTTP 계층에서 공통 관련 io tasks 구성을 담당한다."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from fastapi import WebSocket, WebSocketDisconnect

from server.app.api.http.serializers.audio import build_stream_error_payload, build_stream_payload


logger = logging.getLogger(__name__)


async def receive_stream_messages(
    *,
    websocket: WebSocket,
    session_id: str,
    context_id: str,
    live_stream_service,
    receive_message: Callable[[], Awaitable[bytes | str]],
    to_chunk: Callable[[bytes | str], bytes],
    stream_name: str,
    log_chunk_receive: bool,
    recording_writer,
) -> None:
    """클라이언트 입력을 runtime queue로 전달한다."""

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
            if recording_writer is not None:
                recording_writer.append_chunk(chunk)
            await live_stream_service.enqueue_chunk(context_id, chunk)
    except WebSocketDisconnect:
        logger.info("%s WebSocket 연결 종료: session_id=%s", stream_name, session_id)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.exception("%s WebSocket 수신 실패: session_id=%s", stream_name, session_id)
        await live_stream_service.publish_error(context_id, str(error))
    finally:
        await live_stream_service.close_input(context_id)


async def send_stream_messages(
    *,
    websocket: WebSocket,
    session_id: str,
    context_id: str,
    live_stream_service,
    stream_name: str,
    close_reason: str,
    input_source: str | None,
) -> None:
    """Runtime 결과를 WebSocket payload로 전송한다."""

    try:
        while True:
            result = await live_stream_service.receive_result(context_id)
            if result.terminal:
                return
            if result.error_message is not None:
                await websocket.send_json(
                    build_stream_error_payload(session_id, result.error_message)
                )
                await websocket.close(code=1011, reason=close_reason)
                return
            if result.utterances or result.events:
                logger.info(
                    "%s WebSocket payload 전송: session_id=%s input_source=%s utterances=%d events=%d",
                    stream_name,
                    session_id,
                    input_source,
                    len(result.utterances),
                    len(result.events),
                )
                await websocket.send_json(
                    build_stream_payload(
                        session_id,
                        result.utterances,
                        result.events,
                        input_source=input_source,
                    )
                )
    except WebSocketDisconnect:
        logger.info("%s WebSocket payload 전송 종료: session_id=%s", stream_name, session_id)
