"""노트 보정 job 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.models.note_correction_job import NoteCorrectionJob


class NoteCorrectionJobRepository(ABC):
    """노트 보정 job 저장소 인터페이스."""

    @abstractmethod
    def save(self, job: NoteCorrectionJob) -> NoteCorrectionJob:
        raise NotImplementedError

    @abstractmethod
    def update(self, job: NoteCorrectionJob) -> NoteCorrectionJob:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, job_id: str) -> NoteCorrectionJob | None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_by_session(self, session_id: str) -> NoteCorrectionJob | None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_by_sessions(self, session_ids: list[str]) -> dict[str, NoteCorrectionJob]:
        raise NotImplementedError

    @abstractmethod
    def list_pending(self, limit: int = 10) -> list[NoteCorrectionJob]:
        raise NotImplementedError

    @abstractmethod
    def claim_available(
        self,
        *,
        worker_id: str,
        lease_expires_at: str,
        claimed_at: str,
        limit: int = 10,
    ) -> list[NoteCorrectionJob]:
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
