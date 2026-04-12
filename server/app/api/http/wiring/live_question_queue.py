"""HTTP 계층에서 공통 관련 live question queue 구성을 담당한다."""
from __future__ import annotations

import logging
from functools import lru_cache

from server.app.core.config import settings
from server.app.infrastructure.queues import RedisLiveQuestionStreamQueue

from .job_queue import get_redis_client


logger = logging.getLogger(__name__)


def is_live_question_queue_enabled() -> bool:
    """실시간 질문 큐 활성 여부를 반환한다."""

    return bool(settings.live_question_analysis_enabled and settings.redis_url)


@lru_cache(maxsize=1)
def get_live_question_analysis_queue():
    """실시간 질문 Redis queue를 반환한다."""

    if not is_live_question_queue_enabled():
        return None

    redis_client = get_redis_client()
    if redis_client is None:
        return None

    logger.info(
        "실시간 질문 queue 활성화: request_stream=%s result_stream=%s",
        settings.live_question_request_stream_key,
        settings.live_question_result_stream_key,
    )
    return RedisLiveQuestionStreamQueue(
        redis_client=redis_client,
        request_stream_key=settings.live_question_request_stream_key,
        result_stream_key=settings.live_question_result_stream_key,
        request_group="caps-live-question-workers",
        result_group="caps-live-question-results",
    )
