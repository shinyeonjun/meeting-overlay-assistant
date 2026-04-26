"""Job lease heartbeat 테스트."""

from __future__ import annotations

from server.app.workers.job_lease_heartbeat import JobLeaseHeartbeat


class _FakeLogger:
    def __init__(self) -> None:
        self.warning_calls: list[tuple[str, tuple[object, ...]]] = []
        self.exception_calls: list[tuple[str, tuple[object, ...]]] = []

    def warning(self, message: str, *args: object) -> None:
        self.warning_calls.append((message, args))

    def exception(self, message: str, *args: object) -> None:
        self.exception_calls.append((message, args))


class _SingleLoopStopEvent:
    def __init__(self) -> None:
        self.calls = 0

    def wait(self, _interval_seconds: float) -> bool:
        self.calls += 1
        return self.calls > 1


def test_run이_한번_lease를_갱신한다() -> None:
    calls: list[str] = []
    heartbeat = JobLeaseHeartbeat(
        interval_seconds=1.0,
        renew_lease=lambda: calls.append("renew") or True,
        logger=_FakeLogger(),
        worker_name="worker",
        job_id="job-1",
    )

    heartbeat._run(_SingleLoopStopEvent())

    assert calls == ["renew"]


def test_run이_lease_갱신_실패시_warning후_중단한다() -> None:
    logger = _FakeLogger()
    heartbeat = JobLeaseHeartbeat(
        interval_seconds=1.0,
        renew_lease=lambda: False,
        logger=logger,
        worker_name="worker",
        job_id="job-1",
    )

    heartbeat._run(_SingleLoopStopEvent())

    assert len(logger.warning_calls) == 1
    assert logger.exception_calls == []


def test_running이_context종료시_thread를_정리한다(monkeypatch) -> None:
    logger = _FakeLogger()
    heartbeat = JobLeaseHeartbeat(
        interval_seconds=1.0,
        renew_lease=lambda: True,
        logger=logger,
        worker_name="worker",
        job_id="job-1",
    )
    called: list[object] = []

    def fake_run(stop_event) -> None:
        called.append(stop_event)

    monkeypatch.setattr(heartbeat, "_run", fake_run)

    with heartbeat.running():
        pass

    assert len(called) == 1
