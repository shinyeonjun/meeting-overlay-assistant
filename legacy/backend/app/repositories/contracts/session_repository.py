"""세션 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.domain.models.session import MeetingSession


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
