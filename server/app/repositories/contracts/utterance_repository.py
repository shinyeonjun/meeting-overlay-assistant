"""발화 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.core.persistence_types import ConnectionLike
from server.app.domain.models.utterance import Utterance


class UtteranceRepository(ABC):
    """발화 저장소 인터페이스."""

    @abstractmethod
    def save(
        self,
        utterance: Utterance,
        *,
        connection: ConnectionLike | None = None,
    ) -> Utterance:
        raise NotImplementedError

    @abstractmethod
    def next_sequence(
        self,
        session_id: str,
        *,
        connection: ConnectionLike | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        after_seq_num: int | None = None,
        connection: ConnectionLike | None = None,
    ) -> list[Utterance]:
        raise NotImplementedError

    @abstractmethod
    def list_recent_by_session(
        self,
        session_id: str,
        limit: int,
        *,
        connection: ConnectionLike | None = None,
    ) -> list[Utterance]:
        raise NotImplementedError

    @abstractmethod
    def delete_by_session(
        self,
        session_id: str,
        *,
        connection: ConnectionLike | None = None,
    ) -> int:
        raise NotImplementedError
