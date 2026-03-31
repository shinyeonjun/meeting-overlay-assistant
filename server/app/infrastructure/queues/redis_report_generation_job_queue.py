"""호환 경로용 Redis 큐 래퍼."""

from server.app.infrastructure.queues.redis.report_generation_job_queue import (
    RedisReportGenerationJobQueue,
)

__all__ = ["RedisReportGenerationJobQueue"]
