"""세션 후처리 stage 상태 기록을 담당한다."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from server.app.domain.models.session_post_processing_job import (
    SessionPostProcessingJob,
)
from server.app.domain.session import MeetingSession
from server.app.repositories.contracts.session import SessionRepository


logger = logging.getLogger(__name__)


class PostProcessingStageTracker:
    """후처리 stage 시작/종료 로그와 세션 stage 상태 저장을 묶어 관리한다."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    @contextmanager
    def track(
        self,
        *,
        session: MeetingSession,
        job: SessionPostProcessingJob,
        stage: str,
    ) -> Iterator[MeetingSession]:
        staged_session = self._session_repository.save(
            session.mark_post_processing_stage(stage)
        )
        started_at = time.perf_counter()
        logger.info(
            "session post-processing stage 시작: session_id=%s job_id=%s stage=%s status=%s",
            session.id,
            job.id,
            stage,
            staged_session.post_processing_status,
        )
        try:
            yield staged_session
        except Exception as error:
            logger.warning(
                "session post-processing stage 실패: session_id=%s job_id=%s stage=%s elapsed_seconds=%.3f error=%s",
                session.id,
                job.id,
                stage,
                time.perf_counter() - started_at,
                error,
            )
            raise
        else:
            logger.info(
                "session post-processing stage 완료: session_id=%s job_id=%s stage=%s elapsed_seconds=%.3f",
                session.id,
                job.id,
                stage,
                time.perf_counter() - started_at,
            )
