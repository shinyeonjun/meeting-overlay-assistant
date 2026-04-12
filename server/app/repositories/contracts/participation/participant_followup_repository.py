"""참여자 후속 작업 저장소 계약."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.participation import ParticipantFollowup


class ParticipantFollowupRepository(ABC):
    """참여자 후속 작업 저장소 계약."""

    @abstractmethod
    def upsert_pending(self, followup: ParticipantFollowup) -> ParticipantFollowup:
        raise NotImplementedError

    @abstractmethod
    def mark_resolved(
        self,
        *,
        session_id: str,
        participant_name: str,
        contact_id: str | None = None,
        resolved_by_user_id: str | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(
        self,
        *,
        session_id: str,
        followup_status: str | None = None,
    ) -> list[ParticipantFollowup]:
        raise NotImplementedError
