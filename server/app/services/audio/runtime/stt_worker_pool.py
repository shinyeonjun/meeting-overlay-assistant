"""실시간 STT 워커 풀."""

from __future__ import annotations

import asyncio
import logging

from server.app.services.audio.runtime.inference_result import InferenceResult
from server.app.services.audio.runtime.inference_scheduler import InferenceScheduler


logger = logging.getLogger(__name__)


class STTWorkerPool:
    """공유 스케줄러에서 작업을 가져와 병렬 처리한다."""

    def __init__(self, scheduler: InferenceScheduler, worker_count: int) -> None:
        self._scheduler = scheduler
        self._worker_count = max(worker_count, 1)
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._active_jobs = 0

    @property
    def worker_count(self) -> int:
        return self._worker_count

    def build_snapshot(self) -> dict[str, int]:
        busy_worker_count = self._active_jobs
        return {
            "worker_count": self._worker_count,
            "busy_worker_count": busy_worker_count,
            "idle_worker_count": max(self._worker_count - busy_worker_count, 0),
        }

    async def start(self) -> None:
        if self._worker_tasks:
            return
        self._worker_tasks = [
            asyncio.create_task(self._worker_loop(index), name=f"stt-worker-{index}")
            for index in range(self._worker_count)
        ]

    async def shutdown(self) -> None:
        if not self._worker_tasks:
            return

        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    async def _worker_loop(self, worker_index: int) -> None:
        while True:
            context = None
            try:
                context, job = await self._scheduler.next_job()
                self._active_jobs += 1

                if job.kind == "preview":
                    utterances = await asyncio.to_thread(context.process_preview_chunk, job.chunk)
                    events = []
                else:
                    utterances, events = await asyncio.to_thread(
                        context.process_final_chunk,
                        job.chunk,
                    )

                if utterances or events:
                    await context.publish_result(
                        InferenceResult.payload(utterances=utterances, events=events)
                    )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.exception(
                    "실시간 STT 워커 처리 실패: worker=%s context_id=%s",
                    worker_index,
                    getattr(context, "context_id", "unknown"),
                )
                if context is not None:
                    await context.publish_result(InferenceResult.error(str(error)))
            finally:
                if context is not None and self._active_jobs > 0:
                    self._active_jobs -= 1
                if context is not None:
                    await self._scheduler.complete_job(context.context_id)
