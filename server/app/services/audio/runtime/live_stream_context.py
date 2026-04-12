"""실시간 스트림 처리 컨텍스트."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field

from server.app.services.audio.runtime.inference_result import InferenceResult


@dataclass(slots=True)
class LiveStreamContext:
    """실시간 입력 스트림의 상태를 세션별로 관리한다."""

    context_id: str
    session_id: str
    input_source: str | None
    stream_kind: str
    pipeline_service: object
    max_pending_chunks: int
    _pending_final_chunks: deque[bytes] = field(init=False)
    _pending_preview_chunk: bytes | None = field(default=None, init=False)
    _output_queue: asyncio.Queue[InferenceResult] = field(init=False)
    _busy_job_kind: str | None = field(default=None, init=False)
    _input_closed: bool = field(default=False, init=False)
    _terminal_published: bool = field(default=False, init=False)
    _coalesced_chunk_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._pending_final_chunks = deque()
        self._output_queue = asyncio.Queue()

    @property
    def busy(self) -> bool:
        return self._busy_job_kind is not None

    @property
    def input_closed(self) -> bool:
        return self._input_closed

    @property
    def pending_chunk_count(self) -> int:
        preview_count = 1 if self._pending_preview_chunk is not None else 0
        return len(self._pending_final_chunks) + preview_count

    @property
    def has_pending_chunks(self) -> bool:
        return self.has_pending_final_chunks or self.has_pending_preview_chunk

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
        supports_preview = getattr(self.pipeline_service, "supports_preview", None)
        if callable(supports_preview):
            return bool(supports_preview())
        return False

    @property
    def priority(self) -> str:
        if self._input_closed and self.has_pending_final_chunks:
            return "high"
        return "normal"

    async def enqueue_chunk(self, chunk: bytes) -> None:
        if len(self._pending_final_chunks) >= self.max_pending_chunks:
            self._coalesce_final_tail_chunk(chunk)
        else:
            self._pending_final_chunks.append(chunk)

        if self._input_closed or not self.supports_preview:
            return

        if self._pending_preview_chunk is None:
            self._pending_preview_chunk = chunk
            return

        self._pending_preview_chunk = self._merge_chunks(self._pending_preview_chunk, chunk)
        self._coalesced_chunk_count += 1

    def next_job_kind(self) -> str | None:
        """현재 상태에서 다음으로 꺼낼 job kind를 결정한다."""

        if self._input_closed and self.has_pending_final_chunks:
            return "final"
        if self.supports_preview and self.has_pending_preview_chunk and self.pending_final_chunk_count <= 1:
            return "preview"
        if self.has_pending_final_chunks:
            return "final"
        if self.supports_preview and self.has_pending_preview_chunk:
            return "preview"
        return None

    def pop_job_chunk_nowait(self, job_kind: str) -> bytes:
        if job_kind == "preview":
            if self._pending_preview_chunk is None:
                raise IndexError("pending preview chunk가 없습니다.")
            chunk = self._pending_preview_chunk
            self._pending_preview_chunk = None
            return chunk
        if not self._pending_final_chunks:
            raise IndexError("pending final chunk가 없습니다.")
        return self._pending_final_chunks.popleft()

    def mark_busy(self, job_kind: str) -> None:
        self._busy_job_kind = job_kind

    def mark_idle(self) -> None:
        self._busy_job_kind = None

    def mark_input_closed(self) -> None:
        self._input_closed = True
        # 닫히는 스트림은 preview보다 final drain을 우선한다.
        self._pending_preview_chunk = None

    async def publish_result(self, result: InferenceResult) -> None:
        await self._output_queue.put(result)

    async def next_result(self) -> InferenceResult:
        return await self._output_queue.get()

    async def publish_terminal_once(self) -> None:
        if self._terminal_published:
            return
        self._terminal_published = True
        await self._output_queue.put(InferenceResult.terminal_result())

    def process_preview_chunk(self, chunk: bytes):
        process_preview = getattr(self.pipeline_service, "process_preview_chunk", None)
        if callable(process_preview):
            return process_preview(
                self.session_id,
                chunk,
                self.input_source,
            )
        return []

    def process_final_chunk(self, chunk: bytes):
        process_final = getattr(self.pipeline_service, "process_final_chunk", None)
        if callable(process_final):
            return process_final(
                self.session_id,
                chunk,
                self.input_source,
            )
        return self.pipeline_service.process_chunk(
            self.session_id,
            chunk,
            self.input_source,
        )

    def reset_stream(self) -> None:
        speech_to_text_service = getattr(self.pipeline_service, "_speech_to_text_service", None)
        reset_stream = getattr(speech_to_text_service, "reset_stream", None)
        if callable(reset_stream):
            reset_stream()

    def _coalesce_final_tail_chunk(self, chunk: bytes) -> None:
        if not self._pending_final_chunks:
            self._pending_final_chunks.append(chunk)
            return

        tail_chunk = self._pending_final_chunks.pop()
        merged_chunk = self._merge_chunks(tail_chunk, chunk)
        self._pending_final_chunks.append(merged_chunk)
        self._coalesced_chunk_count += 1

    def _merge_chunks(self, existing_chunk: bytes, new_chunk: bytes) -> bytes:
        if self.stream_kind == "text":
            return existing_chunk + b" " + new_chunk
        return existing_chunk + new_chunk
