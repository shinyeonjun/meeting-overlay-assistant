"""세션 서비스."""

from __future__ import annotations

from backend.app.domain.models.session import MeetingSession
from backend.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from backend.app.repositories.contracts.session_repository import SessionRepository


class SessionService:
    """세션 생성, 종료, 조회와 활성 입력 소스 추적을 담당한다."""

    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    def start_session(self, title: str, mode: SessionMode, source: AudioSource) -> MeetingSession:
        """새 세션을 생성하고 저장한다."""

        session = MeetingSession.start(title=title, mode=mode, source=source)
        return self._session_repository.save(session)

    def end_session(self, session_id: str) -> MeetingSession:
        """기존 세션을 종료한다."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")
        if session.status == SessionStatus.ENDED:
            return session
        return self._session_repository.save(session.end())

    def get_session(self, session_id: str) -> MeetingSession | None:
        """세션 단건을 조회한다."""

        return self._session_repository.get_by_id(session_id)

    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
        """세션에서 실제 활성화된 입력 소스를 기록한다."""

        return self._session_repository.mark_active_source(session_id, input_source)
