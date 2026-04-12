"""최종 전사 recorder."""

from __future__ import annotations

from server.app.services.observability.runtime.metrics_helpers import utc_now_iso
from server.app.services.observability.runtime.runtime_monitor_state import RuntimeMonitorState


def record_final_transcription(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    final_queue_delay_ms: int,
    emitted_live_final: bool,
    alignment_status: str,
    live_final_compare_count: int = 0,
    live_final_changed: bool = False,
    live_final_similarity: float | None = None,
    live_final_delay_ms: int | None = None,
) -> None:
    """최종 전사 결과와 지연 상태를 기록한다."""

    state.recent_finals.append(
        {
            "session_id": session_id,
            "final_queue_delay_ms": final_queue_delay_ms,
            "emitted_live_final": emitted_live_final,
            "alignment_status": alignment_status,
            "live_final_compare_count": live_final_compare_count,
            "live_final_changed": live_final_changed,
            "live_final_similarity": live_final_similarity,
            "live_final_delay_ms": live_final_delay_ms,
            "recorded_at": utc_now_iso(),
        }
    )
