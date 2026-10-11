"""장시간 job 처리 중 lease를 주기적으로 연장하는 helper."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Protocol, TypeVar


class _ClaimedJob(Protocol):
    id: str


_JobT = TypeVar("_JobT", bound=_ClaimedJob)


class JobLeaseHeartbeat:
    """claim한 job들의 lease를 하나의 스레드에서 주기적으로 연장한다.

    batch로 claim하면 batch 안의 모든 job에 lease가 찍히므로, 뒤에 처리될 job도
    앞 job을 처리하는 동안 만료되지 않도록 전부 연장한다. 처리가 끝난 job은 release로 뺀다.
    """

    def __init__(
        self,
        *,
        interval_seconds: float,
        renew_lease: Callable[[str], bool],
        logger: logging.Logger,
        worker_name: str,
        job_ids: Iterable[str],
    ) -> None:
        self._interval_seconds = max(interval_seconds, 1.0)
        self._renew_lease = renew_lease
        self._logger = logger
        self._worker_name = worker_name
        self._active_job_ids = set(job_ids)
        self._lock = threading.Lock()

    def release(self, job_id: str) -> None:
        """처리가 끝난 job은 더 이상 lease를 연장하지 않는다."""

        with self._lock:
            self._active_job_ids.discard(job_id)

    @contextmanager
    def running(self) -> Iterator[None]:
        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name=f"{self._worker_name}-lease-heartbeat",
            daemon=True,
        )
        thread.start()
        try:
            yield
        finally:
            stop_event.set()
            thread.join(timeout=self._interval_seconds + 1.0)

    def _snapshot_active_job_ids(self) -> list[str]:
        with self._lock:
            return list(self._active_job_ids)

    def _run(self, stop_event: threading.Event) -> None:
        while not stop_event.wait(self._interval_seconds):
            for job_id in self._snapshot_active_job_ids():
                try:
                    renewed = self._renew_lease(job_id)
                except Exception:
                    self._logger.exception(
                        "%s lease 연장 실패: job_id=%s",
                        self._worker_name,
                        job_id,
                    )
                    continue

                if not renewed:
                    # 상태가 바뀌었거나 다른 worker에게 넘어간 job이므로 더 연장하지 않는다.
                    self._logger.warning(
                        "%s lease 연장 무시됨: job_id=%s",
                        self._worker_name,
                        job_id,
                    )
                    self.release(job_id)


def resolve_heartbeat_interval_seconds(
    *,
    lease_seconds: int,
    configured_interval_seconds: float,
) -> float:
    """lease 길이의 절반을 넘지 않는 범위에서 heartbeat 간격을 정한다."""

    return max(
        1.0,
        min(float(configured_interval_seconds), max(lease_seconds / 2.0, 1.0)),
    )


def process_claimed_jobs(
    *,
    claimed_jobs: Sequence[_JobT],
    worker_id: str,
    lease_seconds: int,
    heartbeat_interval_seconds: float,
    renew_lease: Callable[..., bool],
    process_job: Callable[..., Any],
    logger: logging.Logger,
    worker_name: str,
) -> list[Any]:
    """claim된 job을 순서대로 처리하는 동안 batch 전체의 lease를 유지한다."""

    heartbeat = JobLeaseHeartbeat(
        interval_seconds=heartbeat_interval_seconds,
        renew_lease=lambda job_id: renew_lease(
            job_id=job_id,
            worker_id=worker_id,
            lease_duration_seconds=lease_seconds,
        ),
        logger=logger,
        worker_name=worker_name,
        job_ids=[job.id for job in claimed_jobs],
    )
    processed: list[Any] = []
    with heartbeat.running():
        for claimed_job in claimed_jobs:
            try:
                processed.append(process_job(claimed_job.id, expected_worker_id=worker_id))
            except Exception:
                # job 하나의 실패가 batch 전체와 worker 프로세스를 멈추지 않게 한다.
                logger.exception(
                    "%s job 처리 중 예외가 났습니다. 나머지 job은 계속 처리합니다: job_id=%s",
                    worker_name,
                    claimed_job.id,
                )
            finally:
                heartbeat.release(claimed_job.id)
    return processed
