"""오디오 영역의 state queries 서비스를 제공한다."""
from __future__ import annotations


def busy_job_kind(context) -> str | None:
    """현재 점유 중인 lane 종류를 반환한다."""

    if context._preview_busy and context._final_busy:
        return "both"
    if context._preview_busy:
        return "preview"
    if context._final_busy:
        return "final"
    return None


def pending_chunk_count(context) -> int:
    """preview/final을 포함한 총 pending chunk 수를 반환한다."""

    preview_count = 1 if context._pending_preview_chunk is not None else 0
    return len(context._pending_final_chunks) + preview_count


def has_pending_chunks(context) -> bool:
    """pending chunk 존재 여부를 반환한다."""

    return context.has_pending_final_chunks or context.has_pending_preview_chunk


def supports_preview(context) -> bool:
    """pipeline이 preview를 지원하는지 반환한다."""

    supports_preview_method = getattr(context.pipeline_service, "supports_preview", None)
    if callable(supports_preview_method):
        return bool(supports_preview_method())
    return False


def priority(context) -> str:
    """현재 context priority를 계산한다."""

    if context._input_closed and context.has_pending_final_chunks:
        return "high"
    return "normal"


def preview_bootstrap_pending(context) -> bool:
    """첫 preview bootstrap이 아직 남아 있는지 반환한다."""

    return supports_preview(context) and not context._input_closed and not context._first_preview_emitted


def is_job_kind_busy(context, job_kind: str) -> bool:
    """주어진 job kind의 lane busy 여부를 반환한다."""

    if job_kind == "preview":
        return context._preview_busy
    if job_kind == "final":
        return context._final_busy
    raise ValueError(f"지원하지 않는 job kind입니다: {job_kind}")
