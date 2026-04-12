"""리포트 영역의 report generation job queue 서비스를 제공한다."""
from __future__ import annotations

from typing import Protocol


class ReportGenerationJobQueue(Protocol):
    """리포트 생성 job 큐 계약."""

    def publish(self, job_id: str) -> bool:
        """job id를 큐에 발행한다."""

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        """큐에서 job id를 기다렸다가 반환한다."""
