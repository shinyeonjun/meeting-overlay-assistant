"""오디오 영역의 live stream context 서비스를 제공한다."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field

from server.app.services.audio.runtime.contexts.helpers import (
    busy_job_kind,
    coalesce_final_tail_chunk,
    enqueue_chunk,
    ensure_preview_cycle_id,
    has_pending_chunks,
    is_job_kind_busy,
    is_job_kind_ready,
    mark_busy,
    mark_idle,
    mark_input_closed,
    merge_chunks,
    next_job_kind,
    pending_chunk_count,
    pop_job_chunk_nowait,
    preferred_ready_kind,
    preview_bootstrap_pending,
    priority,
    process_final_chunk,
    process_preview_chunk,
    ready_job_kinds,
    reset_stream,
    resolve_job_kind,
    should_prioritize_bootstrap_preview,
    supports_preview,
)
from server.app.services.audio.runtime.scheduler.inference_result import InferenceResult


@dataclass(slots=True)
class LiveStreamContext:
    """세션별 pending chunk와 실행 상태를 관리한다."""

    context_id: str
    session_id: str
    input_source: str | None
    stream_kind: str
    pipeline_service: object
    max_pending_chunks: int
    preview_ready_max_pending_finals: int = 2
    _pending_final_chunks: deque[bytes] = field(init=False)
    _pending_preview_chunk: bytes | None = field(default=None, init=False)
    _output_queue: asyncio.Queue[InferenceResult] = field(init=False)
    _preview_busy: bool = field(default=False, init=False)
    _final_busy: bool = field(default=False, init=False)
    _input_closed: bool = field(default=False, init=False)
    _terminal_published: bool = field(default=False, init=False)
    _coalesced_chunk_count: int = field(default=0, init=False)
    _first_preview_emitted: bool = field(default=False, init=False)
    _next_preview_cycle_id: int = field(default=1, init=False)
    _queued_preview_cycle_id: int | None = field(default=None, init=False)
    _active_preview_cycle_id: int | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._pending_final_chunks = deque()
        self._output_queue = asyncio.Queue()

    @property
    def busy(self) -> bool:
        return self._preview_busy or self._final_busy

    @property
    def busy_job_kind(self) -> str | None:
        return busy_job_kind(self)

    @property
    def input_closed(self) -> bool:
        return self._input_closed

    @property
    def pending_chunk_count(self) -> int:
        return pending_chunk_count(self)

    @property
    def has_pending_chunks(self) -> bool:
        return has_pending_chunks(self)

    @property
    def has_pending_final_chunks(self) -> bool:
        return bool(self._pending_final_chunks)

    @property
    def has_pending_preview_chunk(self) -> bool:
        return self._pending_preview_chunk is not None

    @property
    def pending_final_chunk_count(self) -> int:
        return len(self._pending_final_chunks)

    @property
    def coalesced_chunk_count(self) -> int:
        return self._coalesced_chunk_count

    @property
    def supports_preview(self) -> bool:
        return supports_preview(self)

    @property
    def priority(self) -> str:
        return priority(self)

    @property
    def preview_bootstrap_pending(self) -> bool:
        return preview_bootstrap_pending(self)

    @property
    def queued_preview_cycle_id(self) -> int | None:
        return self._queued_preview_cycle_id

    @property
    def active_preview_cycle_id(self) -> int | None:
        return self._active_preview_cycle_id

    async def enqueue_chunk(self, chunk: bytes) -> None:
        await enqueue_chunk(self, chunk)

    def next_job_kind(self) -> str | None:
        return next_job_kind(self)

    def preferred_ready_kind(self) -> str | None:
        return preferred_ready_kind(self)

    def ready_job_kinds(self) -> list[str]:
        return ready_job_kinds(self)

    def is_job_kind_ready(self, job_kind: str) -> bool:
        return is_job_kind_ready(self, job_kind)

    def is_job_kind_busy(self, job_kind: str) -> bool:
        return is_job_kind_busy(self, job_kind)

    def resolve_job_kind(self, preferred_kind: str | None = None) -> str | None:
        return resolve_job_kind(self, preferred_kind)

    def pop_job_chunk_nowait(self, job_kind: str) -> bytes:
        return pop_job_chunk_nowait(self, job_kind)

    def mark_busy(self, job_kind: str) -> None:
        mark_busy(self, job_kind)

    def mark_idle(self, job_kind: str) -> None:
        mark_idle(self, job_kind)

    def mark_preview_emitted(self) -> None:
        self._first_preview_emitted = True

    def mark_input_closed(self) -> None:
        mark_input_closed(self)

    async def publish_result(self, result: InferenceResult) -> None:
        await self._output_queue.put(result)

    async def next_result(self) -> InferenceResult:
        return await self._output_queue.get()

    async def publish_terminal_once(self) -> None:
        if self._terminal_published:
            return
        self._terminal_published = True
        await self._output_queue.put(InferenceResult.terminal_result())

    def ensure_preview_cycle_id(self) -> tuple[int | None, bool]:
        return ensure_preview_cycle_id(self)

    def process_preview_chunk(self, chunk: bytes):
        return process_preview_chunk(self, chunk)

    def process_final_chunk(self, chunk: bytes):
        return process_final_chunk(self, chunk)

    def reset_stream(self) -> None:
        reset_stream(self)

    def _coalesce_final_tail_chunk(self, chunk: bytes) -> None:
        _, coalesced = coalesce_final_tail_chunk(
            pending_final_chunks=self._pending_final_chunks,
            chunk=chunk,
            stream_kind=self.stream_kind,
        )
        self._coalesced_chunk_count += coalesced

    def _merge_chunks(self, existing_chunk: bytes, new_chunk: bytes) -> bytes:
        return merge_chunks(
            existing_chunk=existing_chunk,
            new_chunk=new_chunk,
            stream_kind=self.stream_kind,
        )

    def _should_prioritize_bootstrap_preview(self) -> bool:
        return should_prioritize_bootstrap_preview(self)
