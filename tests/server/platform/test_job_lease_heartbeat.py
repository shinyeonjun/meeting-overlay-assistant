"""batch로 claim한 job 전체의 lease가 처리 순서와 무관하게 유지되는지 검증한다."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from server.app.workers.job_lease_heartbeat import (
    process_claimed_jobs,
    resolve_heartbeat_interval_seconds,
)

logger = logging.getLogger("test-lease-heartbeat")


@dataclass(frozen=True)
class _Job:
    id: str


class _FakeService:
    """job 처리 시간을 줄 수 있고, 어떤 job의 lease가 연장됐는지 기록한다."""

    def __init__(self, durations: dict[str, float], renew_results: dict[str, bool] | None = None):
        self._durations = durations
        self._renew_results = renew_results or {}
        self.renewed: list[str] = []
        self.processed: list[str] = []

    def renew_job_lease(self, *, job_id: str, worker_id: str, lease_duration_seconds: int) -> bool:
        assert worker_id == "worker-1"
        assert lease_duration_seconds == 120
        self.renewed.append(job_id)
        return self._renew_results.get(job_id, True)

    def process_job(self, job_id: str, *, expected_worker_id: str | None = None):
        assert expected_worker_id == "worker-1"
        time.sleep(self._durations.get(job_id, 0.0))
        self.processed.append(job_id)
        return job_id


def _run(service: _FakeService, job_ids: list[str]):
    return process_claimed_jobs(
        claimed_jobs=[_Job(job_id) for job_id in job_ids],
        worker_id="worker-1",
        lease_seconds=120,
        heartbeat_interval_seconds=1.0,
        renew_lease=service.renew_job_lease,
        process_job=service.process_job,
        logger=logger,
        worker_name="test worker",
    )


def test_batch_뒤쪽_job의_lease는_앞_job을_처리하는_동안에도_연장된다():
    service = _FakeService(durations={"job-a": 2.5, "job-b": 0.0})

    processed = _run(service, ["job-a", "job-b"])

    assert processed == ["job-a", "job-b"]
    # job-b는 job-a를 처리하는 동안 대기 중이었으므로, 그 사이에 연장되어야 한다.
    assert "job-b" in service.renewed


def test_처리가_끝난_job의_lease는_더_이상_연장하지_않는다():
    service = _FakeService(durations={"job-a": 0.0, "job-b": 2.5})

    _run(service, ["job-a", "job-b"])

    # job-a는 즉시 끝났으므로 job-b 처리 중에 job-a를 연장하면 안 된다.
    assert "job-a" not in service.renewed
    assert "job-b" in service.renewed


def test_다른_worker에게_넘어간_job은_연장을_멈춘다():
    service = _FakeService(
        durations={"job-a": 2.5},
        renew_results={"job-a": False},
    )

    _run(service, ["job-a"])

    assert service.renewed.count("job-a") == 1


def test_heartbeat_간격은_lease의_절반을_넘지_않는다():
    assert resolve_heartbeat_interval_seconds(lease_seconds=20, configured_interval_seconds=15) == 10.0
    assert resolve_heartbeat_interval_seconds(lease_seconds=120, configured_interval_seconds=15) == 15.0
    assert resolve_heartbeat_interval_seconds(lease_seconds=1, configured_interval_seconds=15) == 1.0


def test_한_job이_예외를_내도_batch의_나머지_job은_계속_처리된다():
    class _FailingFirstService(_FakeService):
        def process_job(self, job_id, *, expected_worker_id=None):
            if job_id == "job-1":
                raise ValueError("다른 worker가 claim한 job")
            return super().process_job(job_id, expected_worker_id=expected_worker_id)

    service = _FailingFirstService(durations={"job-1": 0.0, "job-2": 0.0})

    processed = _run(service, ["job-1", "job-2"])

    assert service.processed == ["job-2"]
    assert processed == ["job-2"]
