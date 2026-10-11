"""실시간 질문 분석 결과 소비자."""

from __future__ import annotations

import asyncio
import logging
import socket


logger = logging.getLogger(__name__)


class LiveQuestionResultConsumer:
    """질문 분석 결과를 읽어 live stream으로 브로드캐스트한다."""

    def __init__(
        self,
        *,
        queue,
        state_store,
        live_stream_service,
        block_seconds: float,
        consumer_name: str | None = None,
    ) -> None:
        self._queue = queue
        self._state_store = state_store
        self._live_stream_service = live_stream_service
        self._block_seconds = max(block_seconds, 0.5)
        self._consumer_name = consumer_name or f"{socket.gethostname()}-live-question-result"
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """백그라운드 소비 루프를 시작한다."""

        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="live-question-result-consumer")

    async def shutdown(self) -> None:
        """백그라운드 소비 루프를 중지한다."""

        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        while True:
            claimed = await asyncio.to_thread(
                self._queue.claim_result,
                consumer_name=self._consumer_name,
                timeout_seconds=self._block_seconds,
            )
            if claimed is None:
                continue

            entry_id, result = claimed
            try:
                events = self._state_store.apply_result(result)
                if events:
                    await self._live_stream_service.publish_question_events(
                        result.session_id,
                        events,
                    )
            except Exception:
                logger.exception(
                    "실시간 질문 결과 반영 실패: session_id=%s window_id=%s",
                    result.session_id,
                    result.window_id,
                )
            finally:
                await asyncio.to_thread(self._queue.ack_result, entry_id)
