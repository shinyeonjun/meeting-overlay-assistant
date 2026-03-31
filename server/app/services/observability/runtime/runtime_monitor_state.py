"""런타임 모니터 상태 컨테이너."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from server.app.services.observability.runtime.preview_cycle_store import PreviewCycleStore


@dataclass(slots=True)
class RuntimeMonitorState:
    """런타임 모니터가 유지하는 최근 상태 묶음."""

    recent_finals: deque[dict[str, object]]
    recent_previews: deque[dict[str, object]]
    preview_cycle_store: PreviewCycleStore
    recent_chunks: deque[dict[str, object]]
    recent_rejections: deque[dict[str, object]]
    recent_backpressure: deque[dict[str, object]]
    recent_errors: deque[dict[str, object]]
    last_chunk_processed_at: str | None = None
    last_error_at: str | None = None
    last_error_message: str | None = None


def build_runtime_monitor_state(
    *,
    final_window_size: int,
    preview_window_size: int,
    chunk_window_size: int,
    rejection_window_size: int,
    backpressure_window_size: int,
    error_window_size: int,
) -> RuntimeMonitorState:
    """윈도우 크기에 맞는 빈 런타임 모니터 상태를 만든다."""

    return RuntimeMonitorState(
        recent_finals=deque(maxlen=final_window_size),
        recent_previews=deque(maxlen=preview_window_size),
        preview_cycle_store=PreviewCycleStore(window_size=preview_window_size),
        recent_chunks=deque(maxlen=chunk_window_size),
        recent_rejections=deque(maxlen=rejection_window_size),
        recent_backpressure=deque(maxlen=backpressure_window_size),
        recent_errors=deque(maxlen=error_window_size),
    )
