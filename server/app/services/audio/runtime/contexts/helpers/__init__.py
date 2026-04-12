"""오디오 영역의   init   서비스를 제공한다."""
from .chunk_queue import coalesce_final_tail_chunk, merge_chunks
from .job_policy import (
    is_job_kind_ready,
    next_job_kind,
    preferred_ready_kind,
    ready_job_kinds,
    resolve_job_kind,
    should_prioritize_bootstrap_preview,
)
from .pipeline_bridge import process_final_chunk, process_preview_chunk, reset_stream
from .state_queries import (
    busy_job_kind,
    has_pending_chunks,
    is_job_kind_busy,
    pending_chunk_count,
    preview_bootstrap_pending,
    priority,
    supports_preview,
)
from .state_transitions import (
    enqueue_chunk,
    ensure_preview_cycle_id,
    mark_busy,
    mark_idle,
    mark_input_closed,
    pop_job_chunk_nowait,
)

__all__ = [
    "busy_job_kind",
    "coalesce_final_tail_chunk",
    "enqueue_chunk",
    "ensure_preview_cycle_id",
    "has_pending_chunks",
    "is_job_kind_ready",
    "is_job_kind_busy",
    "mark_busy",
    "mark_idle",
    "mark_input_closed",
    "merge_chunks",
    "next_job_kind",
    "pending_chunk_count",
    "pop_job_chunk_nowait",
    "preferred_ready_kind",
    "preview_bootstrap_pending",
    "process_final_chunk",
    "process_preview_chunk",
    "priority",
    "ready_job_kinds",
    "reset_stream",
    "resolve_job_kind",
    "should_prioritize_bootstrap_preview",
    "supports_preview",
]
