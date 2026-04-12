"""실시간 추론 작업 스케줄러."""

from __future__ import annotations

import asyncio
from collections import deque

from server.app.services.audio.runtime.inference_job import InferenceJob
from server.app.services.audio.runtime.live_stream_context import LiveStreamContext
from server.app.services.audio.runtime.live_stream_registry import LiveStreamRegistry


class InferenceScheduler:
    """스트림별 대기 작업을 공정하게 배차한다."""

    def __init__(self, registry: LiveStreamRegistry) -> None:
        self._registry = registry
        self._condition = asyncio.Condition()
        self._high_priority_ready_ids: deque[str] = deque()
        self._normal_priority_ready_ids: deque[str] = deque()
        self._high_priority_ready_set: set[str] = set()
        self._normal_priority_ready_set: set[str] = set()

    async def notify_context_ready(self, context_id: str) -> None:
        """처리 가능한 컨텍스트를 우선순위 큐에 올린다."""

        publish_terminal = False
        context: LiveStreamContext | None = None
        async with self._condition:
            context = self._registry.get_context(context_id)
            if context is None:
                self._discard_ready_context(context_id)
                return
            if context.busy:
                return
            if not context.has_pending_chunks:
                self._discard_ready_context(context_id)
                publish_terminal = context.input_closed
            else:
                self._enqueue_ready_context(context_id, context.priority)
                self._condition.notify_all()

        if publish_terminal and context is not None:
            await context.publish_terminal_once()

    async def next_job(self) -> tuple[LiveStreamContext, InferenceJob]:
        """다음으로 처리할 추론 작업을 꺼낸다."""

        while True:
            async with self._condition:
                context = self._pop_next_ready_context()
                if context is None:
                    await self._condition.wait()
                    continue

                job_kind = context.next_job_kind()
                if job_kind is None:
                    if context.input_closed:
                        await context.publish_terminal_once()
                    continue

                context.mark_busy(job_kind)
                chunk = context.pop_job_chunk_nowait(job_kind)
                job = InferenceJob(
                    context_id=context.context_id,
                    session_id=context.session_id,
                    input_source=context.input_source,
                    stream_kind=context.stream_kind,
                    kind=job_kind,
                    priority=context.priority,
                    chunk=chunk,
                )
                return context, job

    async def complete_job(self, context_id: str) -> None:
        """작업 완료 후 다음 상태를 반영한다."""

        publish_terminal = False
        context: LiveStreamContext | None = None
        async with self._condition:
            context = self._registry.get_context(context_id)
            if context is None:
                self._discard_ready_context(context_id)
                return

            context.mark_idle()

            if context.has_pending_chunks:
                self._enqueue_ready_context(context_id, context.priority)
                self._condition.notify_all()
            else:
                self._discard_ready_context(context_id)
                publish_terminal = context.input_closed

        if publish_terminal and context is not None:
            await context.publish_terminal_once()

    def _pop_next_ready_context(self) -> LiveStreamContext | None:
        while self._high_priority_ready_ids:
            context = self._pop_ready_context(
                self._high_priority_ready_ids,
                self._high_priority_ready_set,
            )
            if context is not None:
                return context

        while self._normal_priority_ready_ids:
            context = self._pop_ready_context(
                self._normal_priority_ready_ids,
                self._normal_priority_ready_set,
            )
            if context is not None:
                return context

        return None

    def _pop_ready_context(
        self,
        ready_ids: deque[str],
        ready_set: set[str],
    ) -> LiveStreamContext | None:
        while ready_ids:
            context_id = ready_ids.popleft()
            ready_set.discard(context_id)
            context = self._registry.get_context(context_id)
            if context is None:
                continue
            if context.busy or not context.has_pending_chunks:
                continue
            return context
        return None

    def _enqueue_ready_context(self, context_id: str, priority: str) -> None:
        self._discard_ready_context(context_id)
        if priority == "high":
            self._high_priority_ready_ids.append(context_id)
            self._high_priority_ready_set.add(context_id)
            return
        self._normal_priority_ready_ids.append(context_id)
        self._normal_priority_ready_set.add(context_id)

    def _discard_ready_context(self, context_id: str) -> None:
        self._high_priority_ready_set.discard(context_id)
        self._normal_priority_ready_set.discard(context_id)
        self._high_priority_ready_ids = deque(
            queued_context_id
            for queued_context_id in self._high_priority_ready_ids
            if queued_context_id != context_id
        )
        self._normal_priority_ready_ids = deque(
            queued_context_id
            for queued_context_id in self._normal_priority_ready_ids
            if queued_context_id != context_id
        )
