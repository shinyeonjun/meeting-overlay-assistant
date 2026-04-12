"""발화 저장소 인터페이스."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod

from backend.app.domain.models.utterance import Utterance


class UtteranceRepository(ABC):
    """발화 저장소 인터페이스."""

    @abstractmethod
    def save(
        self,
        utterance: Utterance,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> Utterance:
        raise NotImplementedError

    @abstractmethod
    def next_sequence(
        self,
        session_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(
        self,
        session_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> list[Utterance]:
        raise NotImplementedError

    @abstractmethod
    def list_recent_by_session(
        self,
        session_id: str,
        limit: int,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> list[Utterance]:
        raise NotImplementedError
