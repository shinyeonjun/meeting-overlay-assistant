"""???곕뻣?????덈콦??????????裕??"""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from threading import Event

import pytest

from server.app.services.audio.runtime.scheduler.inference_scheduler import InferenceScheduler
from server.app.services.audio.runtime.contexts.live_stream_registry import LiveStreamRegistry
from server.app.services.audio.runtime.services.live_stream_service import (
    LiveStreamCapacityError,
    LiveStreamService,
)
from server.app.services.audio.runtime.contexts.live_stream_context import LiveStreamContext


class _FakePipelineService:
    def __init__(self, processed: list[tuple[str, str, str]]) -> None:
        self._processed = processed

    def supports_preview(self) -> bool:
        return True

    def process_preview_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        text = chunk.decode("utf-8")
        self._processed.append((session_id, "preview", text))
        return [text]

    def process_final_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        text = chunk.decode("utf-8")
        self._processed.append((session_id, "final", text))
        return [text], []


class _FinalOnlyPipelineService:
    def __init__(self, processed: list[tuple[str, str]]) -> None:
        self._processed = processed

    def process_preview_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        return []

    def process_final_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        text = chunk.decode("utf-8")
        self._processed.append((session_id, text))
        return [text], []


class _ConcurrentPipelineService:
    def __init__(self) -> None:
        self.preview_started = Event()
        self.final_started = Event()

    def supports_preview(self) -> bool:
        return True

    def process_preview_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        self.preview_started.set()
        time.sleep(0.2)
        return [f"preview:{chunk.decode('utf-8')}"]

    def process_final_chunk(self, session_id: str, chunk: bytes, input_source: str | None):
        self.final_started.set()
        time.sleep(0.2)
        return [f"final:{chunk.decode('utf-8')}"], []


class TestLiveStreamRuntime:
    def test_round_robin_distributes_contexts(self):
        async def _scenario() -> None:
            processed: list[tuple[str, str]] = []
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=4,
                max_running_streams=4,
            )
            await service.start()
            try:
                first_context = await service.open_stream(
                    session_id="session-a",
                    input_source="mic",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService(processed),
                )
                second_context = await service.open_stream(
                    session_id="session-b",
                    input_source="mic",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService(processed),
                )

                await service.enqueue_chunk(first_context, b"a-1")
                await service.enqueue_chunk(first_context, b"a-2")
                await service.enqueue_chunk(second_context, b"b-1")

                first_result = await service.receive_result(first_context)
                second_result = await service.receive_result(second_context)
                third_result = await service.receive_result(first_context)

                assert first_result.utterances == ["a-1"]
                assert second_result.utterances == ["b-1"]
                assert third_result.utterances == ["a-2"]
                assert processed == [
                    ("session-a", "a-1"),
                    ("session-b", "b-1"),
                    ("session-a", "a-2"),
                ]
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_closing_input_without_pending_emits_terminal(self):
        async def _scenario() -> None:
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=2,
            )
            await service.start()
            try:
                context_id = await service.open_stream(
                    session_id="session-terminal",
                    input_source="mic",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )
                await service.close_input(context_id)

                result = await service.receive_result(context_id)

                assert result.terminal is True
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_capacity_limit_raises_error(self):
        async def _scenario() -> None:
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=1,
            )
            await service.start()
            try:
                await service.open_stream(
                    session_id="session-1",
                    input_source="mic",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )

                with pytest.raises(LiveStreamCapacityError):
                    await service.open_stream(
                        session_id="session-2",
                        input_source="mic",
                        stream_kind="audio",
                        pipeline_service=_FinalOnlyPipelineService([]),
                    )
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_source_capacity_limit_raises_error(self):
        async def _scenario() -> None:
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=4,
                max_running_streams_by_source={"mic": 1, "system_audio": 2},
            )
            await service.start()
            try:
                await service.open_stream(
                    session_id="session-1",
                    input_source="mic",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )

                with pytest.raises(LiveStreamCapacityError):
                    await service.open_stream(
                        session_id="session-2",
                        input_source="mic",
                        stream_kind="audio",
                        pipeline_service=_FinalOnlyPipelineService([]),
                    )

                system_context_id = await service.open_stream(
                    session_id="session-3",
                    input_source="system_audio",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )

                assert system_context_id.startswith("audio:session-3:")
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_snapshot_includes_live_stream_and_worker_state(self):
        async def _scenario() -> None:
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=3,
                max_running_streams=5,
            )
            await service.start()
            try:
                context_id = await service.open_stream(
                    session_id="session-snapshot",
                    input_source="mic",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )
                await service.enqueue_chunk(context_id, b"hello")

                snapshot = service.build_snapshot()

                assert snapshot["active_stream_count"] == 1
                assert snapshot["pending_chunk_count"] >= 1
                assert snapshot["worker_count"] == 1
                assert snapshot["pending_chunks_per_stream_limit"] == 3
                assert snapshot["max_running_streams"] == 5
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_coalesces_tail_chunk_when_pending_limit_is_reached(self):
        async def _scenario() -> None:
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=2,
            )
            try:
                context_id = await service.open_stream(
                    session_id="session-coalesce",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )

                await service.enqueue_chunk(context_id, b"first")
                await service.enqueue_chunk(context_id, b"second")
                await service.enqueue_chunk(context_id, b"third")

                snapshot = service.build_snapshot()

                assert snapshot["pending_chunk_count"] == 2
                assert snapshot["max_pending_chunk_count"] == 2
                assert snapshot["coalesced_chunk_count"] == 1
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_draining_stream_runs_before_normal_stream(self):
        async def _scenario() -> None:
            processed: list[tuple[str, str]] = []
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=4,
            )
            try:
                first_context = await service.open_stream(
                    session_id="session-normal",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=_FinalOnlyPipelineService(processed),
                )
                second_context = await service.open_stream(
                    session_id="session-draining",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=_FinalOnlyPipelineService(processed),
                )

                await service.enqueue_chunk(first_context, b"normal-1")
                await service.enqueue_chunk(second_context, b"drain-1")
                await service.close_input(second_context)

                await service.start()

                first_result = await service.receive_result(second_context)
                second_result = await service.receive_result(first_context)
                terminal_result = await service.receive_result(second_context)

                assert first_result.utterances == ["drain-1"]
                assert second_result.utterances == ["normal-1"]
                assert terminal_result.terminal is True
                assert processed == [
                    ("session-draining", "drain-1"),
                    ("session-normal", "normal-1"),
                ]
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_preview_and_final_jobs_are_delivered_in_order(self):
        async def _scenario() -> None:
            processed: list[tuple[str, str, str]] = []
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=2,
            )
            await service.start()
            try:
                context_id = await service.open_stream(
                    session_id="session-preview-final",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=_FakePipelineService(processed),
                )

                await service.enqueue_chunk(context_id, b"hello")

                preview_result = await service.receive_result(context_id)
                final_result = await service.receive_result(context_id)

                assert preview_result.utterances == ["hello"]
                assert final_result.utterances == ["hello"]
                assert processed == [
                    ("session-preview-final", "preview", "hello"),
                    ("session-preview-final", "final", "hello"),
                ]
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_preview_bootstrap_prioritizes_preview_before_final_backlog(self):
        async def _scenario() -> None:
            processed: list[tuple[str, str, str]] = []
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=4,
                max_running_streams=2,
            )
            try:
                context_id = await service.open_stream(
                    session_id="session-preview-bootstrap",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=_FakePipelineService(processed),
                )

                await service.enqueue_chunk(context_id, b"hello")
                await service.enqueue_chunk(context_id, b"world")

                await service.start()

                preview_result = await service.receive_result(context_id)
                first_final_result = await service.receive_result(context_id)
                second_final_result = await service.receive_result(context_id)

                assert preview_result.utterances == ["hello world"]
                assert first_final_result.utterances == ["hello"]
                assert second_final_result.utterances == ["world"]
                assert processed == [
                    ("session-preview-bootstrap", "preview", "hello world"),
                    ("session-preview-bootstrap", "final", "hello"),
                    ("session-preview-bootstrap", "final", "world"),
                ]
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_same_context_preview_and_final_start_on_separate_lanes(self):
        async def _scenario() -> None:
            pipeline_service = _ConcurrentPipelineService()
            service = LiveStreamService(
                worker_count=2,
                pending_chunks_per_stream=2,
                max_running_streams=2,
            )
            await service.start()
            try:
                context_id = await service.open_stream(
                    session_id="session-concurrent-lanes",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=pipeline_service,
                )

                await service.enqueue_chunk(context_id, b"hello")

                await asyncio.sleep(0.05)

                assert pipeline_service.preview_started.is_set() is True
                assert pipeline_service.final_started.is_set() is True

                first_result = await service.receive_result(context_id)
                second_result = await service.receive_result(context_id)

                assert sorted(first_result.utterances + second_result.utterances) == [
                    "final:hello",
                    "preview:hello",
                ]
            finally:
                await service.shutdown()

        asyncio.run(_scenario())

    def test_preview_ready_gate_blocks_preview_when_final_backlog_is_two(self):
        async def _scenario() -> None:
            context = LiveStreamContext(
                context_id="text:session-gate:test",
                session_id="session-gate",
                input_source="mic",
                stream_kind="text",
                pipeline_service=_FakePipelineService([]),
                max_pending_chunks=4,
            )

            await context.enqueue_chunk(b"hello")
            await context.enqueue_chunk(b"world")
            context.mark_preview_emitted()

            assert context.pending_final_chunk_count == 2
            assert context.is_job_kind_ready("preview") is True

        asyncio.run(_scenario())

    def test_stale_ready_context도_terminal을_publish한다(self):
        async def _scenario() -> None:
            registry = LiveStreamRegistry(max_running_streams=2)
            scheduler = InferenceScheduler(registry)
            context = registry.create_context(
                session_id="session-terminal-stale",
                input_source="mic",
                stream_kind="audio",
                pipeline_service=object(),
                max_pending_chunks=2,
            )
            await context.enqueue_chunk(b"hello")
            await scheduler.notify_context_ready(context.context_id)

            context.pop_job_chunk_nowait("final")
            context.mark_input_closed()

            next_job_task = asyncio.create_task(scheduler.next_job())
            try:
                result = await asyncio.wait_for(context.next_result(), timeout=0.2)
                assert result.terminal is True
            finally:
                next_job_task.cancel()
                with suppress(asyncio.CancelledError):
                    await next_job_task

        asyncio.run(_scenario())

    def test_publish_question_events는_같은_session_context들에_브로드캐스트한다(self):
        async def _scenario() -> None:
            service = LiveStreamService(
                worker_count=1,
                pending_chunks_per_stream=2,
                max_running_streams=4,
            )
            await service.start()
            try:
                first_context = await service.open_stream(
                    session_id="session-question",
                    input_source="mic",
                    stream_kind="text",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )
                second_context = await service.open_stream(
                    session_id="session-question",
                    input_source="system_audio",
                    stream_kind="audio",
                    pipeline_service=_FinalOnlyPipelineService([]),
                )

                await service.publish_question_events("session-question", ["질문 이벤트"])

                first_result = await service.receive_result(first_context)
                second_result = await service.receive_result(second_context)

                assert first_result.utterances == []
                assert second_result.utterances == []
                assert first_result.events == ["질문 이벤트"]
                assert second_result.events == ["질문 이벤트"]
            finally:
                await service.shutdown()

        asyncio.run(_scenario())
