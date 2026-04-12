"""HTTP 계층에서 공통 관련 session runtime 구성을 담당한다."""
from __future__ import annotations

import logging

from fastapi import WebSocket

from server.app.core.config import settings
from server.app.services.audio.io.session_recording import build_session_recording_path
from server.app.services.audio.io.session_recording_writer import SessionRecordingWriter
from server.app.services.audio.runtime.services.live_stream_service import LiveStreamCapacityError


logger = logging.getLogger(__name__)


def build_recording_writer(
    *,
    session_id: str,
    input_source: str | None,
    stream_kind: str,
) -> SessionRecordingWriter | None:
    """오디오 입력인 경우에만 녹음 writer를 준비한다."""

    if stream_kind != "audio":
        return None

    return SessionRecordingWriter(
        output_path=build_session_recording_path(
            session_id,
            input_source or "audio",
        ),
        sample_rate_hz=settings.stt_sample_rate_hz,
        sample_width_bytes=settings.stt_sample_width_bytes,
        channels=settings.stt_channels,
    )


async def open_stream_context(
    *,
    websocket: WebSocket,
    live_stream_service,
    session_id: str,
    input_source: str | None,
    stream_kind: str,
    pipeline_service,
    stream_name: str,
) -> str | None:
    """이미 accept된 WebSocket에 live runtime context를 연다."""

    try:
        return await live_stream_service.open_stream(
            session_id=session_id,
            input_source=input_source,
            stream_kind=stream_kind,
            pipeline_service=pipeline_service,
        )
    except LiveStreamCapacityError as error:
        logger.warning(
            "%s WebSocket 연결 거절: session_id=%s reason=%s",
            stream_name,
            session_id,
            str(error),
        )
        await websocket.close(code=4429, reason=str(error))
        return None


async def close_stream_context(
    *,
    live_stream_service,
    context_id: str,
    recording_writer: SessionRecordingWriter | None,
) -> None:
    """Runtime context와 녹음 writer를 정리한다."""

    await live_stream_service.close_input(context_id)
    await live_stream_service.close_stream(context_id)
    if recording_writer is not None:
        recording_writer.close()
