"""HTTP 계층에서 공통 관련 websocket streaming 구성을 담당한다."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import WebSocket

from server.app.api.http.dependencies import get_live_stream_service
from server.app.api.http.routes.websocket_streaming_helpers import (
    build_recording_writer,
    close_stream_context,
    open_stream_context,
    receive_stream_messages,
    send_stream_messages,
)


async def stream_bytes(
    *,
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    input_source: str | None,
) -> None:
    """PCM 오디오 바이트 스트림을 live runtime으로 전달한다."""

    await stream_loop(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=pipeline_service,
        receive_message=websocket.receive_bytes,
        to_chunk=lambda message: message,
        stream_name="오디오",
        close_reason="audio pipeline error",
        log_chunk_receive=True,
        input_source=input_source,
        stream_kind="audio",
    )


async def stream_text(
    *,
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    input_source: str | None,
) -> None:
    """텍스트 스트림을 live runtime으로 전달한다."""

    await stream_loop(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=pipeline_service,
        receive_message=websocket.receive_text,
        to_chunk=lambda message: message.encode("utf-8"),
        stream_name="텍스트",
        close_reason="text input pipeline error",
        log_chunk_receive=False,
        input_source=input_source,
        stream_kind="text",
    )


async def stream_loop(
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
    stream_kind: str,
) -> None:
    """공통 loop를 돌려 live runtime과 연결한다."""

    live_stream_service = get_live_stream_service()
    recording_writer = build_recording_writer(
        session_id=session_id,
        input_source=input_source,
        stream_kind=stream_kind,
    )

    context_id = await open_stream_context(
        websocket=websocket,
        live_stream_service=live_stream_service,
        session_id=session_id,
        input_source=input_source,
        stream_kind=stream_kind,
        pipeline_service=pipeline_service,
        stream_name=stream_name,
    )
    if context_id is None:
        return

    receive_task = asyncio.create_task(
        receive_stream_messages(
            websocket=websocket,
            session_id=session_id,
            context_id=context_id,
            live_stream_service=live_stream_service,
            receive_message=receive_message,
            to_chunk=to_chunk,
            stream_name=stream_name,
            log_chunk_receive=log_chunk_receive,
            recording_writer=recording_writer,
        ),
        name=f"{stream_kind}-receive-{session_id}",
    )

    try:
        await send_stream_messages(
            websocket=websocket,
            session_id=session_id,
            context_id=context_id,
            live_stream_service=live_stream_service,
            stream_name=stream_name,
            close_reason=close_reason,
            input_source=input_source,
        )
    finally:
        receive_task.cancel()
        await asyncio.gather(receive_task, return_exceptions=True)
        await close_stream_context(
            live_stream_service=live_stream_service,
            context_id=context_id,
            recording_writer=recording_writer,
        )
