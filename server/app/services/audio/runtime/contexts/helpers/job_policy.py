"""오디오 영역의 job policy 서비스를 제공한다."""
from __future__ import annotations


def should_prioritize_bootstrap_preview(context) -> bool:
    """첫 preview 전까지 bootstrap 우선권을 줄지 판단한다."""

    return context.preview_bootstrap_pending and context.has_pending_preview_chunk


def is_job_kind_ready(context, job_kind: str) -> bool:
    """특정 lane이 지금 실행 가능한지 판단한다."""

    if context.is_job_kind_busy(job_kind):
        return False
    if job_kind == "preview":
        return (
            not context.input_closed
            and context.supports_preview
            and context.has_pending_preview_chunk
            and (
                should_prioritize_bootstrap_preview(context)
                or context.pending_final_chunk_count <= context.preview_ready_max_pending_finals
            )
        )
    if job_kind == "final":
        return context.has_pending_final_chunks
    return False


def preferred_ready_kind(context) -> str | None:
    """scheduler가 우선해서 큐잉할 job kind를 고른다."""

    if context.input_closed and context.has_pending_final_chunks and not context.is_job_kind_busy("final"):
        return "final"
    if should_prioritize_bootstrap_preview(context):
        return "preview"
    if is_job_kind_ready(context, "preview"):
        return "preview"
    if is_job_kind_ready(context, "final"):
        return "final"
    return None


def next_job_kind(context) -> str | None:
    """실행 시점에 실제로 처리할 다음 job kind를 고른다."""

    if context.input_closed and context.has_pending_final_chunks and not context.is_job_kind_busy("final"):
        return "final"
    if is_job_kind_ready(context, "preview"):
        return "preview"
    if is_job_kind_ready(context, "final"):
        return "final"
    return None


def ready_job_kinds(context) -> list[str]:
    """현재 즉시 실행 가능한 job kind 목록을 반환한다."""

    ready_kinds: list[str] = []
    if is_job_kind_ready(context, "preview"):
        ready_kinds.append("preview")
    if is_job_kind_ready(context, "final"):
        ready_kinds.append("final")
    return ready_kinds


def resolve_job_kind(context, preferred_kind: str | None = None) -> str | None:
    """preferred kind를 존중하되 현재 상태에 맞는 실제 job kind를 결정한다."""

    if preferred_kind is not None and is_job_kind_ready(context, preferred_kind):
        return preferred_kind
    if not context.has_pending_chunks:
        return None
    return preferred_ready_kind(context)
