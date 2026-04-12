"""세션 서비스 façade.

기존 의존성 주입 경로를 유지하면서 조회/조정 책임을 분리한 서비스에 위임한다.
"""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.participation import SessionParticipantCandidate
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)
from server.app.services.sessions.session_coordinator import SessionCoordinator
from server.app.services.sessions.session_query_service import SessionQueryService


class SessionService:
    """기존 호출자를 위한 세션 서비스 façade."""

    def __init__(
        self,
        session_repository: SessionRepository,
        meeting_context_repository=None,
    ) -> None:
        participant_resolution_service = ParticipantResolutionService(
            meeting_context_repository=meeting_context_repository,
        )
        self._session_coordinator = SessionCoordinator(
            session_repository=session_repository,
            participant_resolution_service=participant_resolution_service,
        )
        self._session_query_service = SessionQueryService(
            session_repository=session_repository,
            participant_resolution_service=participant_resolution_service,
        )

    def create_session_draft(
        self,
        title: str,
        mode: SessionMode,
        source: AudioSource,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        participants: list[str] | tuple[str, ...] | None = None,
    ) -> MeetingSession:
        """초기 draft 세션을 만든다."""

        return self._session_coordinator.create_session_draft(
            title=title,
            mode=mode,
            source=source,
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            workspace_id=workspace_id,
            participants=participants,
        )

    def start_session(self, session_id: str) -> MeetingSession:
        """기존 draft 세션을 running 상태로 전이한다."""

        return self._session_coordinator.start_session(session_id)

    def end_session(self, session_id: str) -> MeetingSession:
        """기존 세션을 종료한다."""

        return self._session_coordinator.end_session(session_id)

    def get_session(self, session_id: str) -> MeetingSession | None:
        """세션 한 건을 조회한다."""

        return self._session_query_service.get_session(session_id)

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

        return self._session_query_service.list_sessions(
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
        )

    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
        """세션에서 실제 사용된 입력 소스를 기록한다."""

        return self._session_coordinator.mark_active_source(session_id, input_source)

    def count_running_sessions(self) -> int:
        """현재 진행 중인 세션 수를 반환한다."""

        return self._session_query_service.count_running_sessions()

    def build_participant_candidates(
        self,
        *,
        session: MeetingSession,
        workspace_id: str,
    ) -> tuple[SessionParticipantCandidate, ...]:
        """contact로 승격 가능한 참여자 후보를 계산한다."""

        return self._session_query_service.build_participant_candidates(
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

        return self._session_query_service.get_participant_candidate(
            session=session,
            workspace_id=workspace_id,
            participant_name=participant_name,
        )

    def link_participant_contact(
        self,
        *,
        session_id: str,
        participant_name: str,
        contact_id: str,
        account_id: str | None = None,
        email: str | None = None,
        job_title: str | None = None,
        department: str | None = None,
    ) -> MeetingSession:
        """세션 참여자를 contact에 연결하고 저장한다."""

        return self._session_coordinator.link_participant_contact(
            session_id=session_id,
            participant_name=participant_name,
            contact_id=contact_id,
            account_id=account_id,
            email=email,
            job_title=job_title,
            department=department,
        )

    def resolve_ambiguous_participant_contact(
        self,
        *,
        session_id: str,
        workspace_id: str,
        participant_name: str,
        contact_id: str,
    ) -> MeetingSession:
        """동명이인 후보 중 기존 contact를 선택해 연결한다."""

        return self._session_coordinator.resolve_ambiguous_participant_contact(
            session_id=session_id,
            workspace_id=workspace_id,
            participant_name=participant_name,
            contact_id=contact_id,
        )
