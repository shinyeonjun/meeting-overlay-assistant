"""공통 영역의 state ops 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.observability.runtime.recorders.previews import (
    get_preview_cycle_record as read_preview_cycle_record,
)
from server.app.services.observability.runtime.runtime_monitor_snapshot import (
    build_runtime_snapshot,
)
from server.app.services.observability.runtime.runtime_monitor_state import (
    RuntimeMonitorState,
    build_runtime_monitor_state,
)


def reset_state(service) -> None:
    """추적 중인 모니터 상태를 초기화한다."""

    with service._lock:
        service._state = build_runtime_monitor_state(
            final_window_size=service._final_window_size,
            preview_window_size=service._preview_window_size,
            chunk_window_size=service._chunk_window_size,
            rejection_window_size=service._rejection_window_size,
            backpressure_window_size=service._backpressure_window_size,
            error_window_size=service._error_window_size,
        )


def get_preview_cycle_record(
    service,
    *,
    session_id: str,
    preview_cycle_id: int,
    recorded_at_epoch_ms: int,
) -> dict[str, object]:
    """세션별 preview cycle 레코드를 반환한다."""

    return read_preview_cycle_record(
        service._state,
        session_id=session_id,
        preview_cycle_id=preview_cycle_id,
        recorded_at_epoch_ms=recorded_at_epoch_ms,
    )


def build_snapshot(service, *, session_id: str | None = None) -> dict[str, object]:
    """현재 모니터 상태를 API 응답용 dict로 반환한다."""

    with service._lock:
        state: RuntimeMonitorState = service._state
        finals = list(state.recent_finals)
        previews = list(state.recent_previews)
        preview_cycles = state.preview_cycle_store.list_cycles()
        chunks = list(state.recent_chunks)
        rejections = list(state.recent_rejections)
        backpressure = list(state.recent_backpressure)
        errors = list(state.recent_errors)
        last_chunk_processed_at = state.last_chunk_processed_at
        last_error_at = state.last_error_at
        last_error_message = state.last_error_message

    return build_runtime_snapshot(
        finals=finals,
        previews=previews,
        preview_cycles=preview_cycles,
        chunks=chunks,
        rejections=rejections,
        backpressure=backpressure,
        errors=errors,
        last_chunk_processed_at=last_chunk_processed_at,
        last_error_at=last_error_at,
        last_error_message=last_error_message,
        session_id=session_id,
    )
