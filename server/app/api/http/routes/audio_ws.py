"""오디오/텍스트 입력 WebSocket 라우트."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.app.api.http.access_control import can_access_session
from server.app.api.http.dependencies import (
    get_audio_pipeline_service_for_source,
    get_live_stream_service,
    get_session_service,
)
from server.app.api.http.security import authenticate_websocket_if_required
from server.app.api.http.serializers.audio import build_stream_error_payload, build_stream_payload
from server.app.core.config import settings
from server.app.domain.shared.enums import SessionStatus
from server.app.services.audio.io.session_recording import build_session_recording_path
from server.app.services.audio.io.session_recording_writer import SessionRecordingWriter
from server.app.services.audio.runtime.live_stream_service import LiveStreamCapacityError


logger = logging.getLogger(__name__)
router = APIRouter(tags=["audio"])


@router.websocket("/api/v1/ws/audio/{session_id}")
async def audio_stream(websocket: WebSocket, session_id: str) -> None:
    """PCM 오디오를 받아 발화와 이벤트를 생성한다."""

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

    logger.info(
        "오디오 WebSocket 연결 시작: session_id=%s source=%s",
        session_id,
        session.primary_input_source,
    )
    input_source = websocket.query_params.get("input_source") or session.primary_input_source
    session_service.mark_active_source(session_id, input_source)
    await _stream_bytes(
        websocket=websocket,
        session_id=session_id,
        pipeline_service=get_audio_pipeline_service_for_source(input_source),
        input_source=input_source,
    )


async def _stream_bytes(
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    input_source: str | None,
) -> None:
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
        stream_kind="audio",
    )


async def _stream_text(
    websocket: WebSocket,
    session_id: str,
    pipeline_service,
    input_source: str | None,
) -> None:
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
        stream_kind="text",
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
    stream_kind: str,
) -> None:
    live_stream_service = get_live_stream_service()
    await websocket.accept()
    recording_writer: SessionRecordingWriter | None = None

    if stream_kind == "audio":
        recording_writer = SessionRecordingWriter(
            output_path=build_session_recording_path(
                session_id,
                input_source or "audio",
            ),
            sample_rate_hz=settings.stt_sample_rate_hz,
            sample_width_bytes=settings.stt_sample_width_bytes,
            channels=settings.stt_channels,
        )

    try:
        context_id = await live_stream_service.open_stream(
            session_id=session_id,
            input_source=input_source,
            stream_kind=stream_kind,
            pipeline_service=pipeline_service,
        )
    except LiveStreamCapacityError as error:
        logger.warning(
            "%s WebSocket 연결 거부: session_id=%s reason=%s",
            stream_name,
            session_id,
            str(error),
        )
        await websocket.close(code=4429, reason=str(error))
        return

    receive_task = asyncio.create_task(
        _receive_stream_messages(
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
        await _send_stream_messages(
            websocket=websocket,
            session_id=session_id,
            context_id=context_id,
            live_stream_service=live_stream_service,
            stream_name=stream_name,
            close_reason=close_reason,
            input_source=input_source,
        )
    finally:
        await live_stream_service.close_input(context_id)
        receive_task.cancel()
        await asyncio.gather(receive_task, return_exceptions=True)
        await live_stream_service.close_stream(context_id)
        if recording_writer is not None:
            recording_writer.close()


async def _receive_stream_messages(
    *,
    websocket: WebSocket,
    session_id: str,
    context_id: str,
    live_stream_service,
    receive_message: Callable[[], Awaitable[bytes | str]],
    to_chunk: Callable[[bytes | str], bytes],
    stream_name: str,
    log_chunk_receive: bool,
    recording_writer: SessionRecordingWriter | None,
) -> None:
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
        logger.exception("%s WebSocket 수신 처리 실패: session_id=%s", stream_name, session_id)
        await live_stream_service.publish_error(context_id, str(error))
    finally:
        await live_stream_service.close_input(context_id)


async def _send_stream_messages(
    *,
    websocket: WebSocket,
    session_id: str,
    context_id: str,
    live_stream_service,
    stream_name: str,
    close_reason: str,
    input_source: str | None,
) -> None:
    try:
        while True:
            result = await live_stream_service.receive_result(context_id)
            if result.terminal:
                return
            if result.error_message is not None:
                await websocket.send_json(build_stream_error_payload(session_id, result.error_message))
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
        logger.info("%s WebSocket 전송 종료: session_id=%s", stream_name, session_id)
