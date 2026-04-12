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
