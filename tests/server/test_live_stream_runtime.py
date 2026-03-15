"""실시간 스트림 런타임 테스트."""

from __future__ import annotations

import asyncio

import pytest

from server.app.services.audio.runtime.live_stream_service import (
    LiveStreamCapacityError,
    LiveStreamService,
)


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


class TestLiveStreamRuntime:
    def test_서로_다른_컨텍스트를_round_robin으로_배차한다(self):
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

    def test_입력이_닫히고_대기청크가_없으면_terminal을_발행한다(self):
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

    def test_동시_스트림_상한을_넘기면_예외가_발생한다(self):
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

    def test_snapshot이_live_stream과_worker_상태를_집계한다(self):
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

    def test_pending_큐가_가득차면_마지막_청크로_합쳐서_길이를_제한한다(self):
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

    def test_닫히는_스트림은_일반_스트림보다_먼저_drain한다(self):
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

    def test_preview와_final_job을_분리해_순서대로_전달한다(self):
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
