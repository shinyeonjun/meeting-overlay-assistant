"""Redis job 큐 장애 처리 테스트."""

from __future__ import annotations

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from server.app.infrastructure.queues.redis import (
    note_correction_job_queue,
    report_generation_job_queue,
    session_post_processing_job_queue,
)


class _BrokenRedis:
    def blpop(self, *_args, **_kwargs):
        raise RedisConnectionError("connection refused")


@pytest.mark.parametrize(
    ("module", "queue_class_name"),
    [
        (report_generation_job_queue, "RedisReportGenerationJobQueue"),
        (note_correction_job_queue, "RedisNoteCorrectionJobQueue"),
        (session_post_processing_job_queue, "RedisSessionPostProcessingJobQueue"),
    ],
)
def test_redis_장애_시_대기_시간만큼_쉬고_None을_반환한다(monkeypatch, module, queue_class_name):
    slept: list[float] = []
    monkeypatch.setattr(module.time, "sleep", slept.append)
    queue = getattr(module, queue_class_name)(redis_client=_BrokenRedis(), queue_key="caps:test")

    assert queue.wait_for_job(2.5) is None
    assert slept == [3]
