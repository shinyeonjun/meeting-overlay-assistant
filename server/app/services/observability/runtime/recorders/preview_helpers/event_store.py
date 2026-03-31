"""Preview recorder의 공통 event append helper."""

from __future__ import annotations

from server.app.services.observability.runtime.metrics_helpers import utc_now_epoch_ms, utc_now_iso
from server.app.services.observability.runtime.runtime_monitor_state import RuntimeMonitorState


def append_preview_event(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    event_type: str,
    preview_cycle_id: int | None = None,
    **fields: object,
) -> int:
    """Preview 이벤트를 저장하고 기록 시각(epoch ms)을 반환한다."""

    recorded_at_epoch_ms = utc_now_epoch_ms()
    state.recent_previews.append(
        {
            "session_id": session_id,
            "event_type": event_type,
            "preview_cycle_id": preview_cycle_id,
            "recorded_at": utc_now_iso(),
            "recorded_at_epoch_ms": recorded_at_epoch_ms,
            **fields,
        }
    )
    return recorded_at_epoch_ms


def append_preview_backpressure(
    state: RuntimeMonitorState,
    *,
    session_id: str | None,
    final_queue_delay_ms: int,
    hold_chunks: int,
) -> None:
    """Preview backpressure 관련 이벤트를 공통 저장소에 기록한다."""

    recorded_at_epoch_ms = utc_now_epoch_ms()
    recorded_at = utc_now_iso()
    state.recent_backpressure.append(
        {
            "session_id": session_id,
            "final_queue_delay_ms": final_queue_delay_ms,
            "hold_chunks": hold_chunks,
            "recorded_at": recorded_at,
            "recorded_at_epoch_ms": recorded_at_epoch_ms,
        }
    )
    if session_id is None:
        return
    state.recent_previews.append(
        {
            "session_id": session_id,
            "event_type": "backpressure",
            "recorded_at": recorded_at,
            "recorded_at_epoch_ms": recorded_at_epoch_ms,
            "final_queue_delay_ms": final_queue_delay_ms,
            "hold_chunks": hold_chunks,
        }
    )
