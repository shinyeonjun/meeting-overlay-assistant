"""workspace summary 생성 전 실행 타이밍을 조율한다."""

from __future__ import annotations

import logging
import time
from contextlib import nullcontext

from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.session_post_processing_job_repository import (
    SessionPostProcessingJobRepository,
)


logger = logging.getLogger(__name__)


class WorkspaceSummaryExecutionCoordinator:
    """live session과 post-processing 작업이 안정화될 때까지 summary 실행을 조율한다."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        session_post_processing_job_repository: (
            SessionPostProcessingJobRepository | None
        ) = None,
        gpu_heavy_execution_gate=None,
        wait_timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 5.0,
        gpu_heavy_poll_interval_seconds: float = 1.0,
    ) -> None:
        self._session_repository = session_repository
        self._session_post_processing_job_repository = (
            session_post_processing_job_repository
        )
        self._gpu_heavy_execution_gate = gpu_heavy_execution_gate
        self._wait_timeout_seconds = max(wait_timeout_seconds, 0.0)
        self._poll_interval_seconds = max(poll_interval_seconds, 0.1)
        self._gpu_heavy_poll_interval_seconds = max(
            gpu_heavy_poll_interval_seconds,
            0.1,
        )

    def hold(self, *, session_id: str, source_version: int):
        """summary 생성 전 필요한 대기와 GPU gate 획득을 수행한다."""

        self._wait_for_running_sessions_quiet_period(session_id=session_id)
        gate = self._gpu_heavy_execution_gate
        if gate is None:
            self._wait_for_post_processing_quiet_period(session_id=session_id)
            return nullcontext()
        return gate.hold(
            owner=f"workspace_summary:{session_id}:{source_version}",
            poll_interval_seconds=self._gpu_heavy_poll_interval_seconds,
        )

    def _wait_for_running_sessions_quiet_period(self, *, session_id: str) -> None:
        running_session_count = self._session_repository.count_running()
        if running_session_count <= 0:
            return

        deadline = time.monotonic() + self._wait_timeout_seconds
        logger.info(
            "workspace summary live 대기 시작: session_id=%s timeout_seconds=%.1f poll_seconds=%.1f running_session_count=%s",
            session_id,
            self._wait_timeout_seconds,
            self._poll_interval_seconds,
            running_session_count,
        )

        while running_session_count > 0:
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                logger.warning(
                    "workspace summary live 대기 시간 초과, 기존 흐름으로 진행: session_id=%s timeout_seconds=%.1f running_session_count=%s",
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
            "workspace summary live 대기 종료: session_id=%s waited_seconds=%.3f",
            session_id,
            waited_seconds,
        )

    def _wait_for_post_processing_quiet_period(self, *, session_id: str) -> None:
        repository = self._session_post_processing_job_repository
        if repository is None:
            return

        if not repository.has_active_processing_jobs(excluding_session_id=session_id):
            return

        deadline = time.monotonic() + self._wait_timeout_seconds
        logger.info(
            "workspace summary 대기 시작: session_id=%s timeout_seconds=%.1f poll_seconds=%.1f",
            session_id,
            self._wait_timeout_seconds,
            self._poll_interval_seconds,
        )

        while repository.has_active_processing_jobs(excluding_session_id=session_id):
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                logger.warning(
                    "workspace summary 대기 시간 초과, 기존 흐름으로 진행: session_id=%s timeout_seconds=%.1f",
                    session_id,
                    self._wait_timeout_seconds,
                )
                return
            time.sleep(min(self._poll_interval_seconds, remaining_seconds))

        waited_seconds = max(
            self._wait_timeout_seconds - max(deadline - time.monotonic(), 0.0),
            0.0,
        )
        logger.info(
            "workspace summary 대기 종료: session_id=%s waited_seconds=%.3f",
            session_id,
            waited_seconds,
        )
