"""회의 이벤트 저장소 인터페이스."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod

from backend.app.domain.models.meeting_event import MeetingEvent


class MeetingEventRepository(ABC):
    """회의 이벤트 저장소 인터페이스."""

    @abstractmethod
    def save(
        self,
        event: MeetingEvent,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent:
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        event: MeetingEvent,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(
        self,
        session_id: str,
        *,
        insight_scope: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[MeetingEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(
        self,
        event_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent | None:
        raise NotImplementedError

    @abstractmethod
    def find_merge_target(
        self,
        candidate: MeetingEvent,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_source_utterance(
        self,
        session_id: str,
        source_utterance_id: str,
        *,
        insight_scope: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[MeetingEvent]:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        event_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        raise NotImplementedError
