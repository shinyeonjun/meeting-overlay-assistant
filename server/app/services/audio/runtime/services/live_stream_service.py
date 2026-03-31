"""?ㅼ떆媛??ㅽ듃由??고???吏꾩엯 ?쒕퉬??"""

from __future__ import annotations

from server.app.services.audio.runtime.scheduler.inference_result import InferenceResult
from server.app.services.audio.runtime.scheduler.inference_scheduler import InferenceScheduler
from server.app.services.audio.runtime.contexts.live_stream_registry import (
    LiveStreamCapacityError,
    LiveStreamRegistry,
)
from server.app.services.audio.runtime.workers.stt_worker_pool import STTWorkerPool
from server.app.services.observability.runtime.runtime_monitor_service import RuntimeMonitorService


class LiveStreamService:
    """?ㅽ듃由?而⑦뀓?ㅽ듃, ?ㅼ?以꾨윭, ?뚯빱 ???臾띕뒗 facade."""

    def __init__(
        self,
        *,
        worker_count: int,
        pending_chunks_per_stream: int,
        max_running_streams: int,
        runtime_monitor_service: RuntimeMonitorService | None = None,
    ) -> None:
        self._pending_chunks_per_stream = max(pending_chunks_per_stream, 1)
        self._registry = LiveStreamRegistry(max_running_streams=max_running_streams)
        self._scheduler = InferenceScheduler(
            self._registry,
            runtime_monitor_service=runtime_monitor_service,
        )
        self._worker_pool = STTWorkerPool(self._scheduler, worker_count=worker_count)
        self._scheduler.set_busy_worker_count_provider(
            lambda: self._worker_pool.busy_worker_count
        )

    @property
    def worker_count(self) -> int:
        return self._worker_pool.worker_count

    def build_snapshot(self) -> dict[str, object]:
        registry_snapshot = self._registry.build_snapshot()
        worker_snapshot = self._worker_pool.build_snapshot()
        return {
            **registry_snapshot,
            **worker_snapshot,
            "pending_chunks_per_stream_limit": self._pending_chunks_per_stream,
        }

    async def start(self) -> None:
        await self._worker_pool.start()

    async def shutdown(self) -> None:
        await self._worker_pool.shutdown()
        await self._registry.close_all()

    async def open_stream(
        self,
        *,
        session_id: str,
        input_source: str | None,
        stream_kind: str,
        pipeline_service: object,
    ) -> str:
        context = self._registry.create_context(
            session_id=session_id,
            input_source=input_source,
            stream_kind=stream_kind,
            pipeline_service=pipeline_service,
            max_pending_chunks=self._pending_chunks_per_stream,
        )
        return context.context_id

    async def enqueue_chunk(self, context_id: str, chunk: bytes) -> None:
        context = self._require_context(context_id)
        await context.enqueue_chunk(chunk)
        await self._scheduler.notify_context_ready(context_id)

    async def receive_result(self, context_id: str) -> InferenceResult:
        context = self._require_context(context_id)
        return await context.next_result()

    async def publish_error(self, context_id: str, message: str) -> None:
        context = self._registry.get_context(context_id)
        if context is None:
            return
        await context.publish_result(InferenceResult.error(message))

    async def publish_question_events(self, session_id: str, events: list[object]) -> None:
        if not events:
            return
        contexts = self._registry.list_contexts_by_session(session_id)
        if not contexts:
            return
        result = InferenceResult.payload(utterances=[], events=events)
        for context in contexts:
            await context.publish_result(result)

    async def close_input(self, context_id: str) -> None:
        context = self._registry.get_context(context_id)
        if context is None:
            return
        context.mark_input_closed()
        if not context.busy and not context.has_pending_chunks:
            await context.publish_terminal_once()
            return
        if context.has_pending_chunks:
            await self._scheduler.notify_context_ready(context_id)

    async def close_stream(self, context_id: str) -> None:
        await self._registry.remove_context(context_id)

    def _require_context(self, context_id: str):
        context = self._registry.get_context(context_id)
        if context is None:
            raise KeyError(f"?ㅽ듃由?而⑦뀓?ㅽ듃瑜?李얠쓣 ???놁뒿?덈떎: {context_id}")
        return context


__all__ = [
    "LiveStreamCapacityError",
    "LiveStreamService",
]
