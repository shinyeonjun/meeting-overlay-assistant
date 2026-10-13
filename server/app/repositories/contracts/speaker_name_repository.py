"""세션 화자 이름 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.core.persistence_types import ConnectionLike


class SpeakerNameRepository(ABC):
    """화자 라벨에 사용자가 붙인 이름을 저장한다."""

    @abstractmethod
    def list_by_session(
        self,
        session_id: str,
        *,
        transcript_version: int,
        connection: ConnectionLike | None = None,
    ) -> dict[str, str]:
        """주어진 transcript 버전에서 붙인 이름만 {speaker_label: display_name}으로 돌려준다."""
        raise NotImplementedError

    @abstractmethod
    def set_name(
        self,
        session_id: str,
        speaker_label: str,
        display_name: str,
        *,
        transcript_version: int,
        connection: ConnectionLike | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_name(
        self,
        session_id: str,
        speaker_label: str,
        *,
        connection: ConnectionLike | None = None,
    ) -> None:
        raise NotImplementedError
