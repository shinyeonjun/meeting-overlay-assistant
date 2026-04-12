"""세션 영역의 session query service 서비스를 제공한다."""
from __future__ import annotations

from server.app.domain.participation import SessionParticipantCandidate
from server.app.domain.session import MeetingSession
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)


class SessionQueryService:
    """세션 조회와 파생 조회를 담당한다."""

    def __init__(
        self,
        session_repository: SessionRepository,
        participant_resolution_service: ParticipantResolutionService,
    ) -> None:
        self._session_repository = session_repository
        self._participant_resolution_service = participant_resolution_service

    def get_session(self, session_id: str) -> MeetingSession | None:
        """세션 한 건을 조회한다."""

        return self._session_repository.get_by_id(session_id)

    def list_sessions(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 50,
    ) -> list[MeetingSession]:
        """최신 세션 목록을 조회한다."""

        return self._session_repository.list_recent(
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
        )

    def count_running_sessions(self) -> int:
        """현재 진행 중인 세션 수를 반환한다."""

        return self._session_repository.count_running()

    def count_running_sessions_filtered(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        """조건에 맞는 진행 중 세션 수를 반환한다."""

        return self._session_repository.count_running_filtered(
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
        )

    def build_participant_candidates(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
    ) -> tuple[SessionParticipantCandidate, ...]:
        """contact로 승격 가능한 참여자 후보를 계산한다."""

        return self._participant_resolution_service.build_participant_candidates(
            session=session,
            workspace_id=workspace_id,
        )

    def get_participant_candidate(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
        participant_name: str,
    ) -> SessionParticipantCandidate | None:
        """특정 참여자 후보를 찾는다."""

        normalized_name = participant_name.strip()
        if not normalized_name:
            return None

        return self._participant_resolution_service.get_participant_candidate(
            session=session,
            workspace_id=workspace_id,
            participant_name=normalized_name,
        )
