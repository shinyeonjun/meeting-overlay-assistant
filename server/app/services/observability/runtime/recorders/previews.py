"""Preview 관련 recorder facade."""

from __future__ import annotations

from server.app.services.observability.runtime.recorders.preview_helpers import (
    append_preview_backpressure,
    append_preview_event,
    get_preview_cycle_record,
    update_preview_cycle_stage,
)
from server.app.services.observability.runtime.runtime_monitor_state import RuntimeMonitorState


def record_preview_candidate(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    kind: str,
    preview_cycle_id: int | None = None,
) -> None:
    """Preview 또는 live_final 후보 생성 시점을 기록한다."""

    recorded_at_epoch_ms = append_preview_event(
        state,
        session_id=session_id,
        event_type="candidate",
        preview_cycle_id=preview_cycle_id,
        kind=kind,
    )
    update_preview_cycle_stage(
        state,
        session_id=session_id,
        preview_cycle_id=preview_cycle_id,
        stage="candidate",
        recorded_at_epoch_ms=recorded_at_epoch_ms,
    )


def record_preview_emitted(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    kind: str,
    preview_cycle_id: int | None = None,
) -> None:
    """Preview 또는 live_final 실제 전송 시점을 기록한다."""

    recorded_at_epoch_ms = append_preview_event(
        state,
        session_id=session_id,
        event_type="emitted",
        preview_cycle_id=preview_cycle_id,
        kind=kind,
    )
    update_preview_cycle_stage(
        state,
        session_id=session_id,
        preview_cycle_id=preview_cycle_id,
        stage="emitted",
        recorded_at_epoch_ms=recorded_at_epoch_ms,
    )


def record_preview_stage(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    stage: str,
    pending_final_chunk_count: int | None = None,
    busy_worker_count: int | None = None,
    preview_cycle_id: int | None = None,
) -> None:
    """Preview 처리 단계별 타임스탬프를 기록한다."""

    recorded_at_epoch_ms = append_preview_event(
        state,
        session_id=session_id,
        event_type=stage,
        preview_cycle_id=preview_cycle_id,
        pending_final_chunk_count=pending_final_chunk_count,
        busy_worker_count=busy_worker_count,
    )
    update_preview_cycle_stage(
        state,
        session_id=session_id,
        preview_cycle_id=preview_cycle_id,
        stage=stage,
        recorded_at_epoch_ms=recorded_at_epoch_ms,
        pending_final_chunk_count=pending_final_chunk_count,
        busy_worker_count=busy_worker_count,
    )


def record_preview_skip(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    reason: str,
    pending_final_chunk_count: int | None,
    has_pending_preview_chunk: bool | None,
    busy_worker_count: int | None,
    busy_job_kind: str | None,
) -> None:
    """Preview skip 사유를 기록한다."""

    append_preview_event(
        state,
        session_id=session_id,
        event_type="skip",
        reason=reason,
        pending_final_chunk_count=pending_final_chunk_count,
        has_pending_preview_chunk=has_pending_preview_chunk,
        busy_worker_count=busy_worker_count,
        busy_job_kind=busy_job_kind,
    )


def record_preview_rejection(
    state: RuntimeMonitorState,
    *,
    session_id: str,
    reason: str | None,
    filter_stage: str,
) -> None:
    """Preview 후보가 필터에서 탈락한 사유를 기록한다."""

    append_preview_event(
        state,
        session_id=session_id,
        event_type="rejected",
        reason=reason or "unknown",
        filter_stage=filter_stage,
    )


def record_preview_backpressure(
    state: RuntimeMonitorState,
    *,
    session_id: str | None = None,
    final_queue_delay_ms: int,
    hold_chunks: int,
) -> None:
    """Preview backpressure 발생을 기록한다."""

    append_preview_backpressure(
        state,
        session_id=session_id,
        final_queue_delay_ms=final_queue_delay_ms,
        hold_chunks=hold_chunks,
    )


__all__ = [
    "get_preview_cycle_record",
    "record_preview_backpressure",
    "record_preview_candidate",
    "record_preview_emitted",
    "record_preview_rejection",
    "record_preview_skip",
    "record_preview_stage",
]
