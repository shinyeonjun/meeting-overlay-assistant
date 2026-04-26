"""배치 worker entrypoint smoke 테스트."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from server.app.workers import session_post_processing_worker
from server.app.workers.report import generation_worker, note_correction_worker


WORKER_CASES = (
    (generation_worker, "get_report_generation_job_service"),
    (note_correction_worker, "get_note_correction_job_service"),
    (session_post_processing_worker, "get_session_post_processing_job_service"),
)


class _FakeService:
    def __init__(self, jobs: list[object] | None = None) -> None:
        self.jobs = jobs or []
        self.claim_calls: list[dict[str, object]] = []
        self.process_calls: list[tuple[str, str | None]] = []
        self.renew_calls: list[dict[str, object]] = []

    @property
    def has_queue(self) -> bool:
        return True

    def claim_available_jobs(
        self,
        *,
        worker_id: str,
        lease_duration_seconds: int,
        limit: int,
    ) -> list[object]:
        self.claim_calls.append(
            {
                "worker_id": worker_id,
                "lease_duration_seconds": lease_duration_seconds,
                "limit": limit,
            }
        )
        return list(self.jobs)

    def renew_job_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_duration_seconds: int,
    ) -> bool:
        self.renew_calls.append(
            {
                "job_id": job_id,
                "worker_id": worker_id,
                "lease_duration_seconds": lease_duration_seconds,
            }
        )
        return True

    def process_job(self, job_id: str, *, expected_worker_id: str | None = None):
        self.process_calls.append((job_id, expected_worker_id))
        return SimpleNamespace(
            id=job_id,
            session_id=f"session-{job_id}",
            status="completed",
            attempt_count=1,
        )


class _FakeHeartbeat:
    created: list[dict[str, object]] = []

    def __init__(
        self,
        *,
        interval_seconds: float,
        renew_lease,
        logger,
        worker_name: str,
        job_id: str,
    ) -> None:
        self.created.append(
            {
                "interval_seconds": interval_seconds,
                "worker_name": worker_name,
                "job_id": job_id,
            }
        )
        self._renew_lease = renew_lease

    @contextmanager
    def running(self):
        self._renew_lease()
        yield


@pytest.mark.parametrize(("worker_module", "getter_name"), WORKER_CASES)
def test_run_once가_claim된_job을_처리한다(monkeypatch, worker_module, getter_name):
    service = _FakeService(jobs=[SimpleNamespace(id="job-1")])
    _FakeHeartbeat.created = []

    monkeypatch.setattr(worker_module, getter_name, lambda: service)
    monkeypatch.setattr(worker_module, "JobLeaseHeartbeat", _FakeHeartbeat)

    processed_count = worker_module.run_once(
        worker_id="worker-1",
        batch_size=3,
        lease_seconds=120,
    )

    assert processed_count == 1
    assert service.claim_calls == [
        {
            "worker_id": "worker-1",
            "lease_duration_seconds": 120,
            "limit": 3,
        }
    ]
    assert service.process_calls == [("job-1", "worker-1")]
    assert service.renew_calls == [
        {
            "job_id": "job-1",
            "worker_id": "worker-1",
            "lease_duration_seconds": 120,
        }
    ]
    assert _FakeHeartbeat.created[0]["job_id"] == "job-1"


@pytest.mark.parametrize(("worker_module", "getter_name"), WORKER_CASES)
def test_run_once가_claim할_job이_없으면_0을_반환한다(monkeypatch, worker_module, getter_name):
    service = _FakeService(jobs=[])
    monkeypatch.setattr(worker_module, getter_name, lambda: service)

    processed_count = worker_module.run_once(
        worker_id="worker-1",
        batch_size=5,
        lease_seconds=60,
    )

    assert processed_count == 0
    assert service.process_calls == []


@pytest.mark.parametrize(("worker_module", "getter_name"), WORKER_CASES)
def test_main_once가_초기화후_run_once를_호출한다(monkeypatch, worker_module, getter_name):
    service = _FakeService()
    called: dict[str, object] = {}
    log_calls: list[dict[str, object]] = []
    initialize_calls: list[str] = []

    monkeypatch.setattr(worker_module, getter_name, lambda: service)
    monkeypatch.setattr(
        worker_module,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                once=True,
                batch_size=0,
                lease_seconds=1,
                queue_block_seconds=0.1,
                poll_interval_seconds=0.1,
                worker_id="   ",
            )
        ),
    )
    monkeypatch.setattr(worker_module, "build_default_worker_id", lambda: "auto-worker")
    monkeypatch.setattr(
        worker_module,
        "setup_logging",
        lambda **kwargs: log_calls.append(kwargs),
    )
    monkeypatch.setattr(
        worker_module,
        "initialize_primary_persistence",
        lambda: initialize_calls.append("initialized"),
    )
    monkeypatch.setattr(
        worker_module,
        "run_once",
        lambda **kwargs: called.update(kwargs) or 1,
    )

    result = worker_module.main()

    assert result == 0
    assert initialize_calls == ["initialized"]
    assert log_calls
    assert called == {
        "worker_id": "auto-worker",
        "batch_size": 1,
        "lease_seconds": 5,
        "idle_log_level": 20,
    }


@pytest.mark.parametrize("worker_module", [generation_worker, note_correction_worker, session_post_processing_worker])
def test_parser는_heavy_worker_batch_size기본값을_1로_둔다(worker_module):
    parser = worker_module.build_parser()

    args = parser.parse_args([])

    assert args.batch_size == 1
