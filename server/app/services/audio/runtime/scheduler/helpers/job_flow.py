"""scheduler job 흐름 helper."""

from __future__ import annotations

from collections.abc import Callable

from server.app.services.audio.runtime.scheduler.inference_job import InferenceJob


def should_publish_terminal(context) -> bool:
    """context가 terminal 결과를 내보낼 조건인지 판단한다."""

    return context.input_closed and not context.has_pending_chunks and not context.busy


def claim_inference_job(
    *,
    context,
    preferred_kind: str,
    record_preview_stage: Callable[..., None],
) -> InferenceJob:
    """ready context에서 실제 실행할 job을 확정한다."""

    context.mark_busy(preferred_kind)
    chunk = context.pop_job_chunk_nowait(preferred_kind)
    preview_cycle_id = None
    if preferred_kind == "preview":
        preview_cycle_id = context.active_preview_cycle_id
        record_preview_stage(
            context=context,
            stage="picked",
            preview_cycle_id=preview_cycle_id,
        )

    return InferenceJob(
        context_id=context.context_id,
        session_id=context.session_id,
        input_source=context.input_source,
        stream_kind=context.stream_kind,
        kind=preferred_kind,
        priority=context.priority,
        chunk=chunk,
        preview_cycle_id=preview_cycle_id,
    )
