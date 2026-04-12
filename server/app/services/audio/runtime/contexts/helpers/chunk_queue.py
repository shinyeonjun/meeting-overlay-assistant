"""LiveStreamContext chunk queue 유틸리티."""

from __future__ import annotations

from collections import deque


def coalesce_final_tail_chunk(
    *,
    pending_final_chunks: deque[bytes],
    chunk: bytes,
    stream_kind: str,
) -> tuple[deque[bytes], int]:
    """final tail chunk를 coalesce하고 증가한 카운트를 반환한다."""

    if not pending_final_chunks:
        pending_final_chunks.append(chunk)
        return pending_final_chunks, 0

    tail_chunk = pending_final_chunks.pop()
    merged_chunk = merge_chunks(
        existing_chunk=tail_chunk,
        new_chunk=chunk,
        stream_kind=stream_kind,
    )
    pending_final_chunks.append(merged_chunk)
    return pending_final_chunks, 1


def merge_chunks(
    *,
    existing_chunk: bytes,
    new_chunk: bytes,
    stream_kind: str,
) -> bytes:
    """stream kind에 맞게 두 chunk를 합친다."""

    if stream_kind == "text":
        return existing_chunk + b" " + new_chunk
    return existing_chunk + new_chunk
