"""공통 영역의 cycle records 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.observability.runtime.runtime_monitor_state import RuntimeMonitorState


def get_preview_cycle_record(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    preview_cycle_id: int,
    recorded_at_epoch_ms: int,
) -> dict[str, object]:
    """세션별 preview cycle 레코드를 반환한다."""

    return state.preview_cycle_store.get_record(
        session_id=session_id,
        preview_cycle_id=preview_cycle_id,
        recorded_at_epoch_ms=recorded_at_epoch_ms,
    )


def update_preview_cycle_stage(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    preview_cycle_id: int | None,
    stage: str,
    recorded_at_epoch_ms: int,
    pending_final_chunk_count: int | None = None,
    busy_worker_count: int | None = None,
) -> None:
    """Preview cycle에 단계별 첫 시각과 보조 상태를 반영한다."""

    if preview_cycle_id is None:
        return

    preview_cycle = get_preview_cycle_record(
        state,
        session_id=session_id,
        preview_cycle_id=preview_cycle_id,
        recorded_at_epoch_ms=recorded_at_epoch_ms,
    )

    if stage == "candidate":
        state.preview_cycle_store.assign_first_epoch_ms(
            preview_cycle,
            "candidate_at_epoch_ms",
            recorded_at_epoch_ms,
        )
        return

    if stage == "emitted":
        state.preview_cycle_store.assign_first_epoch_ms(
            preview_cycle,
            "emitted_at_epoch_ms",
            recorded_at_epoch_ms,
        )
        return

    if stage == "ready":
        state.preview_cycle_store.assign_first_epoch_ms(
            preview_cycle,
            "ready_at_epoch_ms",
            recorded_at_epoch_ms,
        )
        preview_cycle["ready_pending_final_chunk_count"] = pending_final_chunk_count
        preview_cycle["ready_busy_worker_count"] = busy_worker_count
        return

    if stage == "picked":
        state.preview_cycle_store.assign_first_epoch_ms(
            preview_cycle,
            "picked_at_epoch_ms",
            recorded_at_epoch_ms,
        )
        preview_cycle["picked_pending_final_chunk_count"] = pending_final_chunk_count
        preview_cycle["picked_busy_worker_count"] = busy_worker_count
        return

    if stage == "job_started":
        state.preview_cycle_store.assign_first_epoch_ms(
            preview_cycle,
            "job_started_at_epoch_ms",
            recorded_at_epoch_ms,
        )
        return

    if stage == "sherpa_non_empty":
        state.preview_cycle_store.assign_first_epoch_ms(
            preview_cycle,
            "sherpa_non_empty_at_epoch_ms",
            recorded_at_epoch_ms,
        )
