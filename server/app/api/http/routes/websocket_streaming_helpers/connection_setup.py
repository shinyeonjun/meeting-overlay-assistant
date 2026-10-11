"""WebSocket 연결 준비 helper."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from fastapi import WebSocket
from starlette.concurrency import run_in_threadpool

from server.app.api.http.dependencies import (
    get_audio_pipeline_service_for_source,
    get_session_service,
    get_text_input_pipeline_service,
)
from server.app.api.http.routes.websocket_session_guard import (
    validate_running_session_access,
)
from server.app.api.http.security import (
    accepted_websocket_subprotocol,
    authenticate_websocket_if_required,
)
from server.app.core.config import settings
from server.app.domain.shared.enums import AudioSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedWebSocketConnection:
    """WebSocket stream 시작에 필요한 준비 결과."""

    input_source: str
    pipeline_service: object


_ALLOWED_INPUT_SOURCES = frozenset(source.value for source in AudioSource)


def resolve_requested_input_source(
    websocket: WebSocket,
    session_source: str,
    *,
    default_for_text: str | None = None,
) -> str | None:
    """쿼리의 input_source를 허용된 값으로 검증한다. 잘못된 값이면 None을 돌려준다.

    text 연결은 mic_and_audio 세션에서 기본값을 mic으로 쓴다(default_for_text).
    """

    requested = websocket.query_params.get("input_source")
    if requested:
        return requested if requested in _ALLOWED_INPUT_SOURCES else None
    if default_for_text is not None and session_source == "mic_and_audio":
        return default_for_text
    return session_source


async def prepare_audio_websocket_connection(
    *,
    websocket: WebSocket,
    session_id: str,
) -> PreparedWebSocketConnection | None:
    """오디오 WebSocket 연결에 필요한 세션/소스/pipeline을 준비한다."""

    connect_started_at = perf_counter()
    auth_context = await authenticate_websocket_if_required(websocket)
    if settings.auth_enabled and auth_context is None:
        return None
    auth_elapsed_ms = (perf_counter() - connect_started_at) * 1000

    await websocket.accept(subprotocol=accepted_websocket_subprotocol(websocket))

    session_service = get_session_service()
    session_guard_started_at = perf_counter()
    session = await validate_running_session_access(
        websocket=websocket,
        session_service=session_service,
        session_id=session_id,
        auth_context=auth_context,
    )
    if session is None:
        return None
    session_guard_elapsed_ms = (perf_counter() - session_guard_started_at) * 1000

    logger.info(
        "오디오 WebSocket 연결 수락: session_id=%s source=%s",
        session_id,
        session.primary_input_source,
    )
    input_source = resolve_requested_input_source(websocket, session.primary_input_source)
    if input_source is None:
        await websocket.close(code=4400, reason="알 수 없는 input_source입니다.")
        return None

    mark_source_started_at = perf_counter()
    await run_in_threadpool(session_service.mark_active_source, session_id, input_source)
    mark_source_elapsed_ms = (perf_counter() - mark_source_started_at) * 1000

    pipeline_build_started_at = perf_counter()
    pipeline_service = get_audio_pipeline_service_for_source(input_source)
    pipeline_build_elapsed_ms = (perf_counter() - pipeline_build_started_at) * 1000

    logger.info(
        "오디오 WebSocket 연결 준비 완료: session_id=%s auth_ms=%.1f session_guard_ms=%.1f mark_source_ms=%.1f pipeline_build_ms=%.1f total_pre_accept_ms=%.1f",
        session_id,
        auth_elapsed_ms,
        session_guard_elapsed_ms,
        mark_source_elapsed_ms,
        pipeline_build_elapsed_ms,
        auth_elapsed_ms + session_guard_elapsed_ms,
    )
    return PreparedWebSocketConnection(
        input_source=input_source,
        pipeline_service=pipeline_service,
    )


async def prepare_text_websocket_connection(
    *,
    websocket: WebSocket,
    session_id: str,
) -> PreparedWebSocketConnection | None:
    """텍스트 WebSocket 연결에 필요한 세션/소스/pipeline을 준비한다."""

    auth_context = await authenticate_websocket_if_required(websocket)
    if settings.auth_enabled and auth_context is None:
        return None

    await websocket.accept(subprotocol=accepted_websocket_subprotocol(websocket))

    session_service = get_session_service()
    session = await validate_running_session_access(
        websocket=websocket,
        session_service=session_service,
        session_id=session_id,
        auth_context=auth_context,
    )
    if session is None:
        return None

    input_source = resolve_requested_input_source(
        websocket,
        session.primary_input_source,
        default_for_text="mic",
    )
    if input_source is None:
        await websocket.close(code=4400, reason="알 수 없는 input_source입니다.")
        return None
    await run_in_threadpool(session_service.mark_active_source, session_id, input_source)
    return PreparedWebSocketConnection(
        input_source=input_source,
        pipeline_service=get_text_input_pipeline_service(),
    )
