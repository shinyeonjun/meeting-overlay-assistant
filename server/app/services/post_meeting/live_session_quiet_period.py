"""실시간 회의가 진행 중일 때 후처리 job 실행을 잠시 미룬다."""

from __future__ import annotations

import logging
import time

from server.app.repositories.contracts.session import SessionRepository


logger = logging.getLogger(__name__)


class LiveSessionQuietPeriod:
    """실시간 세션과 GPU heavy 후처리 job이 겹치지 않도록 대기한다."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        wait_timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> None:
        self._session_repository = session_repository
        self._wait_timeout_seconds = max(wait_timeout_seconds, 0.0)
        self._poll_interval_seconds = max(poll_interval_seconds, 0.1)

    def should_defer_claim(self, *, worker_id: str) -> bool:
        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return False

        logger.info(
            "session post-processing job claim 보류: worker_id=%s running_session_count=%s",
            worker_id,
            running_session_count,
        )
        return True

    def wait(self, *, job_id: str, session_id: str) -> None:
        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return

        deadline = time.monotonic() + self._wait_timeout_seconds
        logger.info(
            "session post-processing live 대기 시작: job_id=%s session_id=%s timeout_seconds=%.1f poll_seconds=%.1f running_session_count=%s",
            job_id,
            session_id,
            self._wait_timeout_seconds,
            self._poll_interval_seconds,
            running_session_count,
        )

        while running_session_count > 0:
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                logger.warning(
                    "session post-processing live 대기시간 초과, 기존 흐름으로 진행: job_id=%s session_id=%s timeout_seconds=%.1f running_session_count=%s",
                    job_id,
                    session_id,
                    self._wait_timeout_seconds,
                    running_session_count,
                )
                return
            time.sleep(min(self._poll_interval_seconds, remaining_seconds))
            running_session_count = self._session_repository.count_running()

        waited_seconds = max(
            self._wait_timeout_seconds - max(deadline - time.monotonic(), 0.0),
            0.0,
        )
        logger.info(
            "session post-processing live 대기 종료: job_id=%s session_id=%s waited_seconds=%.3f",
            job_id,
            session_id,
            waited_seconds,
        )
