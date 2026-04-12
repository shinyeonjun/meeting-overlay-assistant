"""Redis 기반 세션 후처리 job 큐."""

from __future__ import annotations

import logging
import math

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - 선택 의존성
    Redis = None

    class RedisError(Exception):
        """redis 패키지가 없을 때를 위한 대체 예외."""


logger = logging.getLogger(__name__)


class RedisSessionPostProcessingJobQueue:
    """Redis list를 이용해 세션 후처리 job을 깨우는 큐."""

    def __init__(
        self,
        *,
        redis_client: Redis,
        queue_key: str,
    ) -> None:
        self._redis_client = redis_client
        self._queue_key = queue_key

    def publish(self, job_id: str) -> bool:
        """job id를 큐에 적재한다."""

        try:
            self._redis_client.rpush(self._queue_key, job_id)
            return True
        except RedisError:
            logger.exception(
                "session post-processing job 큐 발행 실패: queue_key=%s job_id=%s",
                self._queue_key,
                job_id,
            )
            return False

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        """큐에서 job id를 기다렸다가 반환한다."""

        timeout = max(1, math.ceil(timeout_seconds))
        try:
            result = self._redis_client.blpop(self._queue_key, timeout=timeout)
        except RedisError:
            logger.exception(
                "session post-processing job 큐 대기 실패: queue_key=%s timeout_seconds=%s",
                self._queue_key,
                timeout_seconds,
            )
            return None

        if result is None:
            return None

        _, raw_job_id = result
        if isinstance(raw_job_id, bytes):
            return raw_job_id.decode("utf-8", errors="ignore")
        return str(raw_job_id)
