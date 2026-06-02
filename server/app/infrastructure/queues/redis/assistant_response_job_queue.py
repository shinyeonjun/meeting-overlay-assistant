"""Redis based assistant response job queue."""

from __future__ import annotations

import logging
import math

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - optional dependency
    Redis = None

    class RedisError(Exception):
        """Fallback exception when redis is not installed."""


logger = logging.getLogger(__name__)


class RedisAssistantResponseJobQueue:
    """Redis list queue for assistant response job ids."""

    def __init__(self, *, redis_client: Redis, queue_key: str) -> None:
        self._redis_client = redis_client
        self._queue_key = queue_key

    def publish(self, job_id: str) -> bool:
        try:
            self._redis_client.rpush(self._queue_key, job_id)
            return True
        except RedisError:
            logger.exception(
                "assistant response job queue publish failed: queue_key=%s job_id=%s",
                self._queue_key,
                job_id,
            )
            return False

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        timeout = max(1, math.ceil(timeout_seconds))
        try:
            result = self._redis_client.blpop(self._queue_key, timeout=timeout)
        except RedisError:
            logger.exception(
                "assistant response job queue wait failed: queue_key=%s timeout_seconds=%s",
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
