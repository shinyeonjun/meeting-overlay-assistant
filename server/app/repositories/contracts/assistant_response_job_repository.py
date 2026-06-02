"""Assistant response job repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.models.assistant_response_job import AssistantResponseJob


class AssistantResponseJobRepository(ABC):
    """Persistence contract for assistant response jobs."""

    @abstractmethod
    def save(self, job: AssistantResponseJob) -> AssistantResponseJob:
        raise NotImplementedError

    @abstractmethod
    def update(self, job: AssistantResponseJob) -> AssistantResponseJob:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, job_id: str) -> AssistantResponseJob | None:
        raise NotImplementedError

    @abstractmethod
    def list_pending(self, limit: int = 10) -> list[AssistantResponseJob]:
        raise NotImplementedError

    @abstractmethod
    def claim_available(
        self,
        *,
        worker_id: str,
        lease_expires_at: str,
        claimed_at: str,
        limit: int = 10,
    ) -> list[AssistantResponseJob]:
        raise NotImplementedError

    @abstractmethod
    def renew_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_expires_at: str,
    ) -> bool:
        raise NotImplementedError
