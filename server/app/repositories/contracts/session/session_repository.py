"""세션 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.session import MeetingSession


class SessionRepository(ABC):
    """세션 저장소 인터페이스."""

    @abstractmethod
    def save(self, session: MeetingSession) -> MeetingSession:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, session_id: str) -> MeetingSession | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_running(self, *, limit: int = 500) -> list[MeetingSession]:
        raise NotImplementedError

    @abstractmethod
    def touch_runtime_heartbeat(self, session_ids, *, heartbeat_at: str) -> int:
        """live 프로세스가 들고 있는 running 세션의 하트비트를 갱신한다."""
        raise NotImplementedError

    @abstractmethod
    def get_runtime_heartbeat_at(self, session_id: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def list_running_with_stale_heartbeat(
        self,
        *,
        heartbeat_cutoff: str,
        limit: int = 500,
    ) -> list[MeetingSession]:
        raise NotImplementedError

    @abstractmethod
    def mark_recovery_required_if_running(
        self,
        session_id: str,
        *,
        recovery_reason: str,
        recovery_detected_at: str,
    ) -> MeetingSession | None:
        raise NotImplementedError

    @abstractmethod
    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
        raise NotImplementedError

    @abstractmethod
    def list_recent(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 50,
    ) -> list[MeetingSession]:
        raise NotImplementedError

    @abstractmethod
    def count_running(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_running_filtered(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        raise NotImplementedError
