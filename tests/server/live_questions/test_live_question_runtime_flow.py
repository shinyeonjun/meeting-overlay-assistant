"""Live question queue/worker/consumer 테스트."""

from __future__ import annotations

import asyncio

import pytest

import server.app.workers.live_question_worker as live_question_worker_module
from server.app.infrastructure.queues.redis.live_question_stream_queue import (
    RedisError,
    RedisLiveQuestionStreamQueue,
    ResponseError,
)
from server.app.services.live_questions.models import (
    LiveQuestionItem,
    LiveQuestionOperation,
    LiveQuestionRequest,
    LiveQuestionResult,
    LiveQuestionUtterance,
)
from server.app.services.live_questions.question_analysis_worker_service import (
    LiveQuestionAnalysisWorkerService,
)
from server.app.services.live_questions.question_result_consumer import (
    LiveQuestionResultConsumer,
)


class _FakeRedisClient:
    def __init__(
        self,
        *,
        busygroup: bool = False,
        fail_xadd: bool = False,
        fail_xreadgroup: bool = False,
        fail_xack: bool = False,
    ) -> None:
        self._busygroup = busygroup
        self._fail_xadd = fail_xadd
        self._fail_xreadgroup = fail_xreadgroup
        self._fail_xack = fail_xack
        self.groups: list[tuple[str, str]] = []
        self.entries: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.acks: list[tuple[str, str, str]] = []

    def xgroup_create(self, *, name: str, groupname: str, id: str, mkstream: bool) -> None:
        del id, mkstream
        if self._busygroup:
            self._busygroup = False
            raise ResponseError("BUSYGROUP Consumer Group name already exists")
        self.groups.append((name, groupname))

    def xadd(self, stream_key: str, fields: dict[str, str]) -> None:
        if self._fail_xadd:
            raise RedisError("xadd failed")
        entry_id = f"{len(self.entries.get(stream_key, [])) + 1}-0"
        self.entries.setdefault(stream_key, []).append((entry_id, fields))

    def xreadgroup(
        self,
        *,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int,
        block: int,
    ):
        del groupname, consumername, count, block
        if self._fail_xreadgroup:
            raise RedisError("xreadgroup failed")
        stream_key = next(iter(streams))
        queued = self.entries.get(stream_key, [])
        if not queued:
            return []
        entry_id, payload = queued.pop(0)
        return [(stream_key, [(entry_id.encode("utf-8"), {"payload": payload["payload"]})])]

    def xack(self, stream_key: str, group_name: str, entry_id: str) -> None:
        if self._fail_xack:
            raise RedisError("xack failed")
        self.acks.append((stream_key, group_name, entry_id))


class _FakeWorkerQueue:
    def __init__(self, request: LiveQuestionRequest | None = None) -> None:
        self.request = request
        self.published_results: list[LiveQuestionResult] = []
        self.acked_requests: list[str] = []

    def claim_request(self, *, consumer_name: str, timeout_seconds: float):
        del consumer_name, timeout_seconds
        if self.request is None:
            return None
        request = self.request
        self.request = None
        return "request-1", request

    def publish_result(self, result: LiveQuestionResult) -> bool:
        self.published_results.append(result)
        return True

    def ack_request(self, entry_id: str) -> None:
        self.acked_requests.append(entry_id)


class _FakeConsumerQueue:
    def __init__(self, claimed) -> None:
        self._claimed_items = [claimed, None, None]
        self.acked_results: list[str] = []

    def claim_result(self, *, consumer_name: str, timeout_seconds: float):
        del consumer_name, timeout_seconds
        if self._claimed_items:
            return self._claimed_items.pop(0)
        return None

    def ack_result(self, entry_id: str) -> None:
        self.acked_results.append(entry_id)


class _FakeLLMClient:
    def __init__(self, result: LiveQuestionResult | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.calls: list[LiveQuestionRequest] = []
        self.warmed_up = False

    def analyze(self, request: LiveQuestionRequest) -> LiveQuestionResult:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result

    def warm_up(self) -> None:
        self.warmed_up = True


class _FakeStateStore:
    def __init__(self, *, events=None, error: Exception | None = None) -> None:
        self._events = events or []
        self._error = error
        self.calls: list[LiveQuestionResult] = []

    def apply_result(self, result: LiveQuestionResult):
        self.calls.append(result)
        if self._error is not None:
            raise self._error
        return list(self._events)


class _FakeLiveStreamService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[object]]] = []

    async def publish_question_events(self, session_id: str, events: list[object]) -> None:
        self.calls.append((session_id, events))


def _build_request() -> LiveQuestionRequest:
    return LiveQuestionRequest(
        session_id="session-1",
        window_id="window-1",
        utterances=(
            LiveQuestionUtterance(
                id="utt-1",
                text="다음 배포 일정 언제 확정하나요?",
                speaker_label="SPEAKER_00",
                timestamp_ms=1000,
                confidence=0.91,
            ),
        ),
        open_questions=(
            LiveQuestionItem(
                id="q-1",
                summary="기존 질문",
                confidence=0.8,
            ),
        ),
    )


def _build_result() -> LiveQuestionResult:
    return LiveQuestionResult(
        session_id="session-1",
        window_id="window-1",
        operations=(
            LiveQuestionOperation(
                op="add",
                summary="배포 일정 확인 질문",
                confidence=0.88,
                evidence_utterance_ids=("utt-1",),
            ),
        ),
    )


def test_redis_stream_queue가_request와_result를_roundtrip한다() -> None:
    queue = RedisLiveQuestionStreamQueue(
        redis_client=_FakeRedisClient(),
        request_stream_key="request-stream",
        result_stream_key="result-stream",
        request_group="request-group",
        result_group="result-group",
    )
    request = _build_request()
    result = _build_result()

    assert queue.publish_request(request) is True
    claimed_request_id, claimed_request = queue.claim_request(
        consumer_name="consumer-1",
        timeout_seconds=0.1,
    )
    assert claimed_request_id == "1-0"
    assert claimed_request == request
    queue.ack_request(claimed_request_id)

    assert queue.publish_result(result) is True
    claimed_result_id, claimed_result = queue.claim_result(
        consumer_name="consumer-1",
        timeout_seconds=0.1,
    )
    assert claimed_result_id == "1-0"
    assert claimed_result == result
    queue.ack_result(claimed_result_id)


def test_redis_stream_queue가_busygroup은_무시하고_publish오류는_false를_반환한다() -> None:
    queue = RedisLiveQuestionStreamQueue(
        redis_client=_FakeRedisClient(busygroup=True, fail_xadd=True),
        request_stream_key="request-stream",
        result_stream_key="result-stream",
        request_group="request-group",
        result_group="result-group",
    )

    assert queue.publish_request(_build_request()) is False


def test_question_analysis_worker_service가_결과를_발행하고_ack한다() -> None:
    request = _build_request()
    result = _build_result()
    queue = _FakeWorkerQueue(request=request)
    llm_client = _FakeLLMClient(result=result)
    service = LiveQuestionAnalysisWorkerService(queue=queue, llm_client=llm_client)

    processed = service.process_next_request(
        consumer_name="consumer-1",
        timeout_seconds=0.1,
    )

    assert processed == result
    assert llm_client.calls == [request]
    assert queue.published_results == [result]
    assert queue.acked_requests == ["request-1"]


def test_question_analysis_worker_service가_실패해도_ack한다() -> None:
    queue = _FakeWorkerQueue(request=_build_request())
    llm_client = _FakeLLMClient(error=RuntimeError("analysis failed"))
    service = LiveQuestionAnalysisWorkerService(queue=queue, llm_client=llm_client)

    processed = service.process_next_request(
        consumer_name="consumer-1",
        timeout_seconds=0.1,
    )

    assert processed is None
    assert queue.published_results == []
    assert queue.acked_requests == ["request-1"]


def test_live_question_result_consumer가_결과를_state_store와_live_stream에_반영한다() -> None:
    result = _build_result()
    queue = _FakeConsumerQueue(("result-1", result))
    state_store = _FakeStateStore(events=["evt-1"])
    live_stream_service = _FakeLiveStreamService()
    consumer = LiveQuestionResultConsumer(
        queue=queue,
        state_store=state_store,
        live_stream_service=live_stream_service,
        block_seconds=0.01,
        consumer_name="consumer-1",
    )

    async def _run() -> None:
        await consumer.start()
        await asyncio.sleep(0.05)
        await consumer.shutdown()

    asyncio.run(_run())

    assert state_store.calls == [result]
    assert live_stream_service.calls == [("session-1", ["evt-1"])]
    assert queue.acked_results == ["result-1"]


def test_live_question_result_consumer가_반영_실패해도_ack한다() -> None:
    queue = _FakeConsumerQueue(("result-1", _build_result()))
    state_store = _FakeStateStore(error=RuntimeError("apply failed"))
    live_stream_service = _FakeLiveStreamService()
    consumer = LiveQuestionResultConsumer(
        queue=queue,
        state_store=state_store,
        live_stream_service=live_stream_service,
        block_seconds=0.01,
        consumer_name="consumer-1",
    )

    async def _run() -> None:
        await consumer.start()
        await asyncio.sleep(0.05)
        await consumer.shutdown()

    asyncio.run(_run())

    assert live_stream_service.calls == []
    assert queue.acked_results == ["result-1"]


def test_live_question_worker가_queue없으면_에러를_낸다(monkeypatch) -> None:
    monkeypatch.setattr(
        live_question_worker_module,
        "get_live_question_analysis_queue",
        lambda: None,
    )

    with pytest.raises(RuntimeError):
        live_question_worker_module.build_worker_service()


def test_live_question_worker가_queue와_llm_client를_묶어_서비스를_만든다(monkeypatch) -> None:
    queue = object()
    captured: dict[str, object] = {}

    class _FakeLiveQuestionLLMClient:
        def __init__(self, **kwargs) -> None:
            captured["llm_kwargs"] = kwargs

    class _FakeWorkerService:
        def __init__(self, *, queue, llm_client) -> None:
            captured["queue"] = queue
            captured["llm_client"] = llm_client

    monkeypatch.setattr(
        live_question_worker_module,
        "get_live_question_analysis_queue",
        lambda: queue,
    )
    monkeypatch.setattr(
        live_question_worker_module,
        "LiveQuestionLLMClient",
        _FakeLiveQuestionLLMClient,
    )
    monkeypatch.setattr(
        live_question_worker_module,
        "LiveQuestionAnalysisWorkerService",
        _FakeWorkerService,
    )

    service = live_question_worker_module.build_worker_service()

    assert isinstance(service, _FakeWorkerService)
    assert captured["queue"] is queue
    assert captured["llm_kwargs"]["model"] == live_question_worker_module.settings.live_question_llm_model


def test_live_question_worker_main_once가_단건_처리를_호출한다(monkeypatch) -> None:
    calls: list[tuple[str, float]] = []
    fake_worker = type(
        "FakeWorker",
        (),
        {
            "process_next_request": lambda self, *, consumer_name, timeout_seconds: calls.append(
                (consumer_name, timeout_seconds)
            )
        },
    )()

    monkeypatch.setattr(
        live_question_worker_module,
        "build_parser",
        lambda: type(
            "FakeParser",
            (),
            {
                "parse_args": lambda self: type(
                    "Args",
                    (),
                    {
                        "once": True,
                        "consumer_name": "consumer-1",
                        "block_seconds": 2.5,
                    },
                )()
            },
        )(),
    )
    monkeypatch.setattr(live_question_worker_module, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        live_question_worker_module,
        "settings",
        type(
            "FakeSettings",
            (),
            {
                "live_question_analysis_enabled": True,
                "log_level": "INFO",
                "log_json": False,
                "log_file_path": None,
            },
        )(),
    )
    monkeypatch.setattr(live_question_worker_module, "build_worker_service", lambda: fake_worker)
    monkeypatch.setattr(live_question_worker_module, "warm_up_worker_service", lambda worker: None)

    result = live_question_worker_module.main()

    assert result == 0
    assert calls == [("consumer-1", 2.5)]


def test_live_question_worker_main은_비활성화되면_worker를_만들지_않는다(monkeypatch) -> None:
    monkeypatch.setattr(
        live_question_worker_module,
        "build_parser",
        lambda: type(
            "FakeParser",
            (),
            {
                "parse_args": lambda self: type(
                    "Args",
                    (),
                    {
                        "once": True,
                        "consumer_name": "consumer-1",
                        "block_seconds": 2.5,
                    },
                )()
            },
        )(),
    )
    monkeypatch.setattr(live_question_worker_module, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(
        live_question_worker_module,
        "settings",
        type(
            "FakeSettings",
            (),
            {
                "live_question_analysis_enabled": False,
                "log_level": "INFO",
                "log_json": False,
                "log_file_path": None,
            },
        )(),
    )
    monkeypatch.setattr(
        live_question_worker_module,
        "build_worker_service",
        lambda: pytest.fail("disabled worker should not be built"),
    )

    result = live_question_worker_module.main()

    assert result == 0
