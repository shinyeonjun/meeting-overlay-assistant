"""Assistant response job queue protocol."""

from __future__ import annotations

from typing import Protocol


class AssistantResponseJobQueue(Protocol):
    """Queue abstraction used to wake assistant response workers."""

    def publish(self, job_id: str) -> bool:
        raise NotImplementedError

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        raise NotImplementedError
