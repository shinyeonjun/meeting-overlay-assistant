"""공통 영역의 runtime events 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.observability.runtime.metrics_helpers import utc_now_iso
from server.app.services.observability.runtime.runtime_monitor_state import RuntimeMonitorState


def record_rejection(state: RuntimeMonitorState, *, reason: str | None) -> None:
    """전사 필터 사유를 기록한다."""

    state.recent_rejections.append(
        {
            "reason": reason or "unknown",
            "recorded_at": utc_now_iso(),
        }
    )


def record_chunk_processed(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    utterance_count: int,
    event_count: int,
) -> None:
    """Chunk 처리 결과를 기록한다."""

    processed_at = utc_now_iso()
    state.recent_chunks.append(
        {
            "session_id": session_id,
            "utterance_count": utterance_count,
            "event_count": event_count,
            "processed_at": processed_at,
        }
    )
    state.last_chunk_processed_at = processed_at


def record_error(state: RuntimeMonitorState, *, scope: str, message: str) -> None:
    """최근 오류를 기록한다."""

    recorded_at = utc_now_iso()
    state.recent_errors.append(
        {
            "scope": scope,
            "message": message,
            "recorded_at": recorded_at,
        }
    )
    state.last_error_at = recorded_at
    state.last_error_message = f"{scope}: {message}"
