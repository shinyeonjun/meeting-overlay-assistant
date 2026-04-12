"""공통 영역의 test live question worker 동작을 검증한다."""
from __future__ import annotations

from server.app.workers.live_question_worker import warm_up_worker_service


class TestLiveQuestionWorker:
    """worker startup warm-up 동작을 검증한다."""

    def test_warm_up_worker_service가_worker_warm_up을_호출한다(self):
        called = {"value": False}

        class FakeWorker:
            def warm_up(self) -> None:
                called["value"] = True

        warm_up_worker_service(FakeWorker())

        assert called["value"] is True

    def test_warm_up_worker_service는_실패해도_예외를_삼킨다(self):
        class FailingWorker:
            def warm_up(self) -> None:
                raise RuntimeError("warmup failed")

        warm_up_worker_service(FailingWorker())
