"""장시간 job 처리 중 lease를 주기적으로 연장하는 helper."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Callable, Iterator


class JobLeaseHeartbeat:
    """백그라운드에서 lease 연장을 반복한다."""

    def __init__(
        self,
        *,
        interval_seconds: float,
        renew_lease: Callable[[], bool],
        logger: logging.Logger,
        worker_name: str,
        job_id: str,
    ) -> None:
        self._interval_seconds = max(interval_seconds, 1.0)
        self._renew_lease = renew_lease
        self._logger = logger
        self._worker_name = worker_name
        self._job_id = job_id

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

    def _run(self, stop_event: threading.Event) -> None:
        while not stop_event.wait(self._interval_seconds):
            try:
                renewed = self._renew_lease()
            except Exception:
                self._logger.exception(
                    "%s lease 연장 실패: job_id=%s",
                    self._worker_name,
                    self._job_id,
                )
                return

            if not renewed:
                self._logger.warning(
                    "%s lease 연장 무시됨: job_id=%s",
                    self._worker_name,
                    self._job_id,
                )
                return
