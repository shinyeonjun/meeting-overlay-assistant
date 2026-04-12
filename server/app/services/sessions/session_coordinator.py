"""세션 라이프사이클 조정 서비스."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)


class SessionCoordinator:
    """세션 생성, 전이, 참여자 연결을 조정한다."""

    def __init__(
        self,
        session_repository: SessionRepository,
        participant_resolution_service: ParticipantResolutionService,
    ) -> None:
        self._session_repository = session_repository
        self._participant_resolution_service = participant_resolution_service

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

        participant_links = self._participant_resolution_service.resolve_initial_participant_links(
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            participants=participants,
        )
        session = MeetingSession.create_draft(
            title=title,
            mode=mode,
            source=source,
            created_by_user_id=created_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            participants=participants,
            participant_links=participant_links,
        )
        return self._session_repository.save(session)

    def start_session(self, session_id: str) -> MeetingSession:
        """기존 draft 세션을 running 상태로 전이한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        return self._session_repository.save(session.start_running())

    def end_session(self, session_id: str) -> MeetingSession:
        """기존 세션을 종료한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        return self._session_repository.save(session.end())

    def rename_session(self, session_id: str, title: str) -> MeetingSession:
        """세션 제목을 변경한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        return self._session_repository.save(session.rename_title(title))

    def delete_session(self, session_id: str) -> bool:
        """세션과 cascade 연결 데이터를 함께 삭제한다."""

        return self._session_repository.delete(session_id)

    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
        """세션에서 실제 사용된 입력 소스를 기록한다."""

        return self._session_repository.mark_active_source(session_id, input_source)

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

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        updated_session = session.link_participant_contact(
            participant_name,
            contact_id=contact_id,
            account_id=account_id,
            email=email,
            job_title=job_title,
            department=department,
        )
        return self._session_repository.save(updated_session)

    def resolve_ambiguous_participant_contact(
        self,
        *,
        session_id: str,
        workspace_id: str,
        participant_name: str,
        contact_id: str,
    ) -> MeetingSession:
        """동명이인 후보 중 기존 contact를 선택해 연결한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")

        candidate = self._participant_resolution_service.get_participant_candidate(
            session=session,
            workspace_id=workspace_id,
            participant_name=participant_name,
        )
        if candidate is None:
            raise ValueError("contact 후보가 아닌 참여자입니다.")
        if candidate.resolution_status != "ambiguous":
            raise ValueError("동명이인 선택이 필요한 참여자가 아닙니다.")

        matched_contact = next(
            (item for item in candidate.matched_contacts if item.contact_id == contact_id),
            None,
        )
        if matched_contact is None:
            raise ValueError("해당 contact가 ambiguous 후보 목록에 없습니다.")

        return self.link_participant_contact(
            session_id=session_id,
            participant_name=participant_name,
            contact_id=matched_contact.contact_id,
            account_id=matched_contact.account_id or candidate.account_id,
            email=matched_contact.email,
            job_title=matched_contact.job_title,
            department=matched_contact.department,
        )
