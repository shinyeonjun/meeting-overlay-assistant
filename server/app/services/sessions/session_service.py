"""세션 서비스 facade."""

from __future__ import annotations

import shutil
from pathlib import Path

from server.app.core.config import settings
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.participation import SessionParticipantCandidate
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)
from server.app.services.sessions.session_coordinator import SessionCoordinator
from server.app.services.sessions.session_query_service import SessionQueryService
from server.app.services.sessions.session_recovery_service import SessionRecoveryService


class SessionService:
    """기존 호출자를 위한 세션 서비스 facade."""

    def __init__(
        self,
        session_repository: SessionRepository,
        meeting_context_repository=None,
        *,
        recovery_service: SessionRecoveryService | None = None,
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
        self._recovery_service = recovery_service

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

    def rename_session(self, session_id: str, title: str) -> MeetingSession:
        """세션 제목을 변경한다."""

        return self._session_coordinator.rename_session(session_id, title)

    def delete_session(self, session_id: str) -> None:
        """세션과 관련 artifacts를 삭제한다."""

        session = self._get_session_or_raise(session_id)
        session = self._recover_orphaned_running_session(session)
        if session.status == SessionStatus.RUNNING:
            raise ValueError("진행 중인 회의는 먼저 종료해야 삭제할 수 있습니다.")

        deleted = self._session_coordinator.delete_session(session_id)
        if not deleted:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        self._delete_session_artifacts(session_id)

    def prepare_session_for_reprocess(self, session_id: str) -> MeetingSession:
        """노트 재생성 전에 세션 상태를 정리한다."""

        session = self._get_session_or_raise(session_id)
        session = self._recover_orphaned_running_session(session)
        if session.status == SessionStatus.RUNNING:
            raise ValueError("진행 중인 회의는 노트를 다시 만들 수 없습니다.")
        return session

    def get_session(self, session_id: str) -> MeetingSession | None:
        """세션 상세를 조회한다."""

        return self._session_query_service.get_session(session_id)

    @staticmethod
    def _delete_session_artifacts(session_id: str) -> None:
        artifacts_root = Path(settings.artifacts_root_path)
        for target in (
            artifacts_root / "recordings" / session_id,
            artifacts_root / "reports" / session_id,
            artifacts_root / "clips" / session_id,
            artifacts_root / "transcript_corrections" / session_id,
            artifacts_root / "workspace_summaries" / session_id,
        ):
            shutil.rmtree(target, ignore_errors=True)

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
        """세션에서 실제 사용한 입력 소스를 기록한다."""

        return self._session_coordinator.mark_active_source(session_id, input_source)

    def count_running_sessions(self) -> int:
        """현재 진행 중인 세션 수를 반환한다."""

        return self._session_query_service.count_running_sessions()

    def count_running_sessions_filtered(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        """조건에 맞는 진행 중 세션 수를 반환한다."""

        return self._session_query_service.count_running_sessions_filtered(
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
        """contact로 연결 가능한 참여자 후보를 계산한다."""

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

    def _get_session_or_raise(self, session_id: str) -> MeetingSession:
        session = self._session_query_service.get_session(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        return session

    def _recover_orphaned_running_session(self, session: MeetingSession) -> MeetingSession:
        if session.status != SessionStatus.RUNNING or self._recovery_service is None:
            return session
        recovered = self._recovery_service.recover_session_if_orphaned(session.id)
        return recovered or session
