"""이벤트 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.core.persistence_types import ConnectionLike
from server.app.domain.events import MeetingEvent


class MeetingEventRepository(ABC):
    """회의 이벤트 저장소 인터페이스."""

    @abstractmethod
    def save(
        self,
        event: MeetingEvent,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        event: MeetingEvent,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(
        self,
        session_id: str,
        *,
        insight_scope: str | None = None,
        connection: ConnectionLike | None = None,
    ) -> list[MeetingEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        event_id: str,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent | None:
        raise NotImplementedError

    @abstractmethod
    def find_merge_target(
        self,
        candidate: MeetingEvent,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_source_utterance(
        self,
        session_id: str,
        source_utterance_id: str,
        *,
        insight_scope: str | None = None,
        connection: ConnectionLike | None = None,
    ) -> list[MeetingEvent]:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        event_id: str,
        *,
        connection: ConnectionLike | None = None,
    ) -> None:
        raise NotImplementedError
