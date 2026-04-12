"""라이브 스트림 추론 스케줄러."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Callable

from server.app.services.audio.runtime.contexts.live_stream_context import LiveStreamContext
from server.app.services.audio.runtime.contexts.live_stream_registry import LiveStreamRegistry
from server.app.services.audio.runtime.scheduler.helpers import (
    claim_inference_job,
    discard_ready_context,
    enqueue_ready_context,
    pop_next_ready_context,
    record_preview_skip_if_needed,
    record_preview_stage,
    should_publish_terminal,
)
from server.app.services.audio.runtime.scheduler.inference_job import InferenceJob
from server.app.services.observability.runtime.runtime_monitor_service import RuntimeMonitorService


class InferenceScheduler:
    """라이브 스트림 context를 kind별 queue로 조정하는 스케줄러."""

    def __init__(
        self,
        registry: LiveStreamRegistry,
        *,
        runtime_monitor_service: RuntimeMonitorService | None = None,
    ) -> None:
        self._registry = registry
        self._runtime_monitor_service = runtime_monitor_service
        self._busy_worker_count_provider: Callable[[], int] = lambda: 0
        self._condition = asyncio.Condition()
        self._high_final_ready_ids: deque[str] = deque()
        self._preview_ready_ids: deque[str] = deque()
        self._normal_final_ready_ids: deque[str] = deque()
        self._ready_queue_memberships: dict[str, set[str]] = {}

    def set_busy_worker_count_provider(self, provider: Callable[[], int]) -> None:
        """현재 busy worker 수 조회 함수를 설정한다."""

        self._busy_worker_count_provider = provider

    async def notify_context_ready(self, context_id: str) -> None:
        """context가 준비되었을 때 적절한 ready queue에 등록한다."""

        publish_terminal = False
        context: LiveStreamContext | None = None
        async with self._condition:
            context = self._registry.get_context(context_id)
            if context is None:
                self._discard_ready_context(context_id)
                return

            publish_terminal = self._refresh_context_state(context)

        if publish_terminal and context is not None:
            await context.publish_terminal_once()

    async def next_job(self) -> tuple[LiveStreamContext, InferenceJob]:
        """다음 실행할 job을 꺼낸다."""

        while True:
            publish_terminal_context: LiveStreamContext | None = None
            async with self._condition:
                ready_item = self._pop_next_ready_context()
                if ready_item is None:
                    await self._condition.wait()
                    continue

                context, preferred_kind = ready_item
                if not context.is_job_kind_ready(preferred_kind):
                    if self._refresh_context_state(context):
                        publish_terminal_context = context
                else:
                    job = claim_inference_job(
                        context=context,
                        preferred_kind=preferred_kind,
                        record_preview_stage=self._record_preview_stage,
                    )
                    return context, job

            if publish_terminal_context is not None:
                await publish_terminal_context.publish_terminal_once()

    async def complete_job(self, context_id: str, job_kind: str) -> None:
        """job 완료 후 context를 다시 queue에 올릴지 판단한다."""

        publish_terminal = False
        context: LiveStreamContext | None = None
        async with self._condition:
            context = self._registry.get_context(context_id)
            if context is None:
                self._discard_ready_context(context_id)
                return

            context.mark_idle(job_kind)
            publish_terminal = self._refresh_context_state(context)

        if publish_terminal and context is not None:
            await context.publish_terminal_once()

    def _pop_next_ready_context(self) -> tuple[LiveStreamContext, str] | None:
        return pop_next_ready_context(
            registry=self._registry,
            ready_queue_memberships=self._ready_queue_memberships,
            high_final_ready_ids=self._high_final_ready_ids,
            preview_ready_ids=self._preview_ready_ids,
            normal_final_ready_ids=self._normal_final_ready_ids,
        )

    def _enqueue_ready_kinds(self, context: LiveStreamContext) -> None:
        self._discard_ready_context(context.context_id)
        for ready_kind in context.ready_job_kinds():
            if ready_kind == "preview":
                preview_cycle_id, created = context.ensure_preview_cycle_id()
                if created:
                    self._record_preview_stage(
                        context=context,
                        stage="ready",
                        preview_cycle_id=preview_cycle_id,
                    )
                if preview_cycle_id is None:
                    continue
                if not created and context.queued_preview_cycle_id is None:
                    continue

            self._enqueue_ready_context(
                context_id=context.context_id,
                preferred_kind=ready_kind,
                priority=context.priority,
            )

    def _enqueue_ready_context(self, *, context_id: str, preferred_kind: str, priority: str) -> None:
        enqueue_ready_context(
            context_id=context_id,
            preferred_kind=preferred_kind,
            priority=priority,
            ready_queue_memberships=self._ready_queue_memberships,
            high_final_ready_ids=self._high_final_ready_ids,
            preview_ready_ids=self._preview_ready_ids,
            normal_final_ready_ids=self._normal_final_ready_ids,
        )

    def _discard_ready_context(self, context_id: str) -> None:
        (
            self._high_final_ready_ids,
            self._preview_ready_ids,
            self._normal_final_ready_ids,
        ) = discard_ready_context(
            context_id,
            ready_queue_memberships=self._ready_queue_memberships,
            high_final_ready_ids=self._high_final_ready_ids,
            preview_ready_ids=self._preview_ready_ids,
            normal_final_ready_ids=self._normal_final_ready_ids,
        )

    def _record_preview_stage(
        self,
        *,
        context: LiveStreamContext,
        stage: str,
        preview_cycle_id: int | None = None,
    ) -> None:
        record_preview_stage(
            runtime_monitor_service=self._runtime_monitor_service,
            context=context,
            busy_worker_count_provider=self._busy_worker_count_provider,
            stage=stage,
            preview_cycle_id=preview_cycle_id,
        )

    def _record_preview_skip_if_needed(self, context: LiveStreamContext) -> None:
        record_preview_skip_if_needed(
            runtime_monitor_service=self._runtime_monitor_service,
            context=context,
            busy_worker_count_provider=self._busy_worker_count_provider,
        )

    def _refresh_context_state(self, context: LiveStreamContext) -> bool:
        """queue/skip/terminal 판단에 필요한 context 후처리를 묶는다."""

        self._enqueue_ready_kinds(context)
        self._record_preview_skip_if_needed(context)
        if context.has_pending_chunks:
            self._condition.notify_all()
        return should_publish_terminal(context)
