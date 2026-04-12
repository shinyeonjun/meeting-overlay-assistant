"""오디오 영역의 preview metrics 서비스를 제공한다."""
from __future__ import annotations


def record_preview_stage(
    *,
    runtime_monitor_service,
    context,
    busy_worker_count_provider,
    stage: str,
    preview_cycle_id: int | None = None,
) -> None:
    """preview 처리 단계 타임스탬프를 기록한다."""

    if runtime_monitor_service is None:
        return
    runtime_monitor_service.record_preview_stage(
        session_id=context.session_id,
        stage=stage,
        pending_final_chunk_count=context.pending_final_chunk_count,
        busy_worker_count=busy_worker_count_provider(),
        preview_cycle_id=preview_cycle_id,
    )


def record_preview_skip_if_needed(
    *,
    runtime_monitor_service,
    context,
    busy_worker_count_provider,
) -> None:
    """preview가 skip된 이유를 기록한다."""

    if runtime_monitor_service is None:
        return
    if not context.supports_preview or not context.has_pending_preview_chunk:
        return
    if context.is_job_kind_ready("preview"):
        return

    reason = "busy" if context.is_job_kind_busy("preview") else "preferred_final"
    runtime_monitor_service.record_preview_skip(
        session_id=context.session_id,
        reason=reason,
        pending_final_chunk_count=context.pending_final_chunk_count,
        has_pending_preview_chunk=context.has_pending_preview_chunk,
        busy_worker_count=busy_worker_count_provider(),
        busy_job_kind=context.busy_job_kind,
    )
