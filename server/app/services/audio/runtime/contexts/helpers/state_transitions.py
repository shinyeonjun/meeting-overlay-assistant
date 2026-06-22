"""LiveStreamContext 상태 전이 helper."""

from __future__ import annotations

from server.app.core.config import settings
from server.app.services.audio.runtime.contexts.helpers.chunk_queue import merge_chunks


def _resolve_chunk_source_audio_end_ms(context, chunk: bytes) -> int | None:
    """입력 chunk가 포함하는 오디오 타임라인 끝 위치를 계산한다."""

    if context.stream_kind == "text":
        return None
    bytes_per_ms = int(
        settings.stt_sample_rate_hz
        * settings.stt_sample_width_bytes
        * settings.stt_channels
        / 1000
    )
    if bytes_per_ms <= 0:
        return None
    context._input_audio_cursor_ms += int(round(len(chunk) / bytes_per_ms))
    return context._input_audio_cursor_ms


async def enqueue_chunk(context, chunk: bytes) -> None:
    """입력 chunk를 final/preview 대기열에 반영한다."""

    source_audio_end_ms = _resolve_chunk_source_audio_end_ms(context, chunk)

    if len(context._pending_final_chunks) >= context.max_pending_chunks:
        tail_chunk = context._pending_final_chunks.pop()
        if context._pending_final_chunk_source_audio_end_ms:
            context._pending_final_chunk_source_audio_end_ms.pop()
        context._pending_final_chunks.append(
            merge_chunks(
                existing_chunk=tail_chunk,
                new_chunk=chunk,
                stream_kind=context.stream_kind,
            )
        )
        context._pending_final_chunk_source_audio_end_ms.append(source_audio_end_ms)
        context._coalesced_chunk_count += 1
    else:
        context._pending_final_chunks.append(chunk)
        context._pending_final_chunk_source_audio_end_ms.append(source_audio_end_ms)

    if context._input_closed or not context.supports_preview:
        return

    if context._pending_preview_chunk is None:
        context._pending_preview_chunk = chunk
        context._pending_preview_source_audio_end_ms = source_audio_end_ms
        return

    context._pending_preview_chunk = merge_chunks(
        existing_chunk=context._pending_preview_chunk,
        new_chunk=chunk,
        stream_kind=context.stream_kind,
    )
    context._pending_preview_source_audio_end_ms = source_audio_end_ms
    context._coalesced_chunk_count += 1


def pop_job_chunk_nowait(context, job_kind: str) -> bytes:
    """지정한 lane에서 즉시 처리할 chunk를 꺼낸다."""

    if job_kind == "preview":
        if context._pending_preview_chunk is None:
            raise IndexError("pending preview chunk가 없습니다.")
        chunk = context._pending_preview_chunk
        context._pending_preview_chunk = None
        context._last_popped_source_audio_end_ms = (
            context._pending_preview_source_audio_end_ms
        )
        context._pending_preview_source_audio_end_ms = None
        context._active_preview_cycle_id = context._queued_preview_cycle_id
        context._queued_preview_cycle_id = None
        return chunk
    if not context._pending_final_chunks:
        raise IndexError("pending final chunk가 없습니다.")
    if context._pending_final_chunk_source_audio_end_ms:
        context._last_popped_source_audio_end_ms = (
            context._pending_final_chunk_source_audio_end_ms.popleft()
        )
    else:
        context._last_popped_source_audio_end_ms = None
    return context._pending_final_chunks.popleft()


def mark_busy(context, job_kind: str) -> None:
    """지정한 lane을 busy 상태로 표시한다."""

    if job_kind == "preview":
        context._preview_busy = True
        return
    if job_kind == "final":
        context._final_busy = True
        return
    raise ValueError(f"지원하지 않는 job kind입니다: {job_kind}")


def mark_idle(context, job_kind: str) -> None:
    """지정한 lane을 idle 상태로 되돌린다."""

    if job_kind == "preview":
        context._preview_busy = False
        context._active_preview_cycle_id = None
        return
    if job_kind == "final":
        context._final_busy = False
        return
    raise ValueError(f"지원하지 않는 job kind입니다: {job_kind}")


def mark_input_closed(context) -> None:
    """입력 종료를 표시하고 preview 대기열을 정리한다."""

    context._input_closed = True
    context._pending_preview_chunk = None
    context._pending_preview_source_audio_end_ms = None


def ensure_preview_cycle_id(context) -> tuple[int | None, bool]:
    """현재 preview 대기열에 대응하는 cycle id를 보장한다."""

    if not context.has_pending_preview_chunk:
        return None, False
    if context._queued_preview_cycle_id is not None:
        return context._queued_preview_cycle_id, False
    preview_cycle_id = context._next_preview_cycle_id
    context._next_preview_cycle_id += 1
    context._queued_preview_cycle_id = preview_cycle_id
    return preview_cycle_id, True
