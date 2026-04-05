"""실시간 스트림 컨텍스트 레지스트리."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from server.app.services.audio.runtime.contexts.live_stream_context import LiveStreamContext


class LiveStreamCapacityError(RuntimeError):
    """동시 라이브 스트림 수가 제한을 넘으면 발생한다."""


@dataclass(slots=True)
class LiveStreamRegistry:
    """활성 스트림 컨텍스트를 등록하고 정리한다."""

    max_running_streams: int
    _contexts: dict[str, LiveStreamContext] = field(init=False, default_factory=dict)

    @property
    def active_count(self) -> int:
        return len(self._contexts)

    def create_context(
        self,
        *,
        session_id: str,
        input_source: str | None,
        stream_kind: str,
        pipeline_service: object,
        max_pending_chunks: int,
    ) -> LiveStreamContext:
        if len(self._contexts) >= self.max_running_streams:
            raise LiveStreamCapacityError("실시간 처리 용량이 모두 찼습니다.")

        context_id = f"{stream_kind}:{session_id}:{uuid4().hex}"
        context = LiveStreamContext(
            context_id=context_id,
            session_id=session_id,
            input_source=input_source,
            stream_kind=stream_kind,
            pipeline_service=pipeline_service,
            max_pending_chunks=max_pending_chunks,
        )
        self._contexts[context_id] = context
        return context

    def get_context(self, context_id: str) -> LiveStreamContext | None:
        return self._contexts.get(context_id)

    def list_contexts_by_session(self, session_id: str) -> list[LiveStreamContext]:
        return [
            context
            for context in self._contexts.values()
            if context.session_id == session_id
        ]

    def build_snapshot(self) -> dict[str, int]:
        busy_stream_count = sum(1 for context in self._contexts.values() if context.busy)
        pending_chunk_count = sum(
            context.pending_chunk_count for context in self._contexts.values()
        )
        coalesced_chunk_count = sum(
            context.coalesced_chunk_count for context in self._contexts.values()
        )
        draining_stream_count = sum(
            1 for context in self._contexts.values() if context.input_closed and context.has_pending_chunks
        )
        max_pending_chunk_count = max(
            (context.pending_chunk_count for context in self._contexts.values()),
            default=0,
        )
        return {
            "active_stream_count": len(self._contexts),
            "busy_stream_count": busy_stream_count,
            "idle_stream_count": len(self._contexts) - busy_stream_count,
            "pending_chunk_count": pending_chunk_count,
            "max_pending_chunk_count": max_pending_chunk_count,
            "draining_stream_count": draining_stream_count,
            "coalesced_chunk_count": coalesced_chunk_count,
            "max_running_streams": self.max_running_streams,
        }

    async def remove_context(self, context_id: str) -> None:
        context = self._contexts.pop(context_id, None)
        if context is None:
            return
        context.reset_stream()

    async def close_all(self) -> None:
        context_ids = list(self._contexts.keys())
        for context_id in context_ids:
            await self.remove_context(context_id)
