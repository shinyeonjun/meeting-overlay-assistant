"""PostgreSQL advisory lock 기반 GPU-heavy 실행 gate."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase


logger = logging.getLogger(__name__)


class PostgreSQLGpuExecutionGate:
    """GPU-heavy 구간을 직렬화하는 공용 advisory lock gate."""

    def __init__(
        self,
        database: PostgreSQLDatabase,
        *,
        lock_key: int = 684248763,
        default_poll_interval_seconds: float = 1.0,
    ) -> None:
        self._database = database
        self._lock_key = lock_key
        self._default_poll_interval_seconds = max(default_poll_interval_seconds, 0.1)

    @contextmanager
    def hold(
        self,
        *,
        owner: str,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ) -> Iterator[None]:
        """공용 GPU slot을 획득한 동안만 내부 블록을 실행한다."""

        poll_seconds = max(
            poll_interval_seconds or self._default_poll_interval_seconds,
            0.1,
        )
        deadline = (
            None
            if timeout_seconds is None
            else time.monotonic() + max(timeout_seconds, 0.0)
        )
        waited_seconds = 0.0
        connection = self._database.connect()
        acquired = False

        try:
            while True:
                row = connection.execute(
                    "SELECT pg_try_advisory_lock(%s) AS acquired",
                    (self._lock_key,),
                ).fetchone()
                if row and row["acquired"]:
                    acquired = True
                    break

                if deadline is not None:
                    remaining_seconds = deadline - time.monotonic()
                    if remaining_seconds <= 0:
                        raise TimeoutError(
                            f"GPU-heavy gate 획득 시간 초과: owner={owner}",
                        )
                    sleep_seconds = min(poll_seconds, remaining_seconds)
                else:
                    sleep_seconds = poll_seconds

                time.sleep(sleep_seconds)
                waited_seconds += sleep_seconds

            logger.info(
                "gpu-heavy gate 획득: owner=%s waited_seconds=%.3f",
                owner,
                waited_seconds,
            )
            yield
        finally:
            if acquired:
                try:
                    connection.execute(
                        "SELECT pg_advisory_unlock(%s) AS released",
                        (self._lock_key,),
                    ).fetchone()
                except Exception:
                    logger.exception("gpu-heavy gate 해제 실패: owner=%s", owner)
            connection.close()
