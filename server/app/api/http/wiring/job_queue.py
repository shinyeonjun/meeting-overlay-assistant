"""비동기 job 큐 조립."""

from __future__ import annotations

import logging
from functools import lru_cache

from server.app.core.config import settings
from server.app.infrastructure.queues import RedisReportGenerationJobQueue

try:
    from redis import Redis
except ImportError:  # pragma: no cover - 선택 의존성
    Redis = None


logger = logging.getLogger(__name__)


def is_report_job_queue_enabled() -> bool:
    """리포트 생성 job 큐 사용 여부를 반환한다."""

    return bool(settings.redis_url)


@lru_cache(maxsize=1)
def get_redis_client():
    """Redis 클라이언트를 캐시한다."""

    if not settings.redis_url:
        return None
    if Redis is None:
        raise RuntimeError("REDIS_URL을 사용하려면 redis 패키지 설치가 필요합니다.")
    return Redis.from_url(settings.redis_url)


@lru_cache(maxsize=1)
def get_report_generation_job_queue():
    """리포트 생성 job 큐 구현체를 반환한다."""

    redis_client = get_redis_client()
    if redis_client is None:
        return None
    logger.info(
        "report job 큐 활성화: queue_key=%s",
        settings.report_job_queue_key,
    )
    return RedisReportGenerationJobQueue(
        redis_client=redis_client,
        queue_key=settings.report_job_queue_key,
    )
