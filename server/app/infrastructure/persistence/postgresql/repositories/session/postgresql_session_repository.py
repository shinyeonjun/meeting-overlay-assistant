"""PostgreSQL 세션 저장소 구현."""

from __future__ import annotations

from server.app.domain.participation import SessionParticipant
from server.app.domain.session import MeetingSession
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories.session.session_helpers import (
    build_session_from_row,
    delete_session_row,
    fetch_recent_session_rows,
    fetch_running_session_rows,
    fetch_running_session_count,
    fetch_running_session_count_filtered,
    fetch_session_row,
    list_session_participants,
    mark_session_recovery_required_if_running,
    rebuild_session,
    replace_session_participants,
    upsert_session,
)
from server.app.repositories.contracts.session import SessionRepository


class PostgreSQLSessionRepository(SessionRepository):
    """PostgreSQL 기반 세션 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def save(self, session: MeetingSession) -> MeetingSession:
        """세션과 참여자 링크를 함께 저장한다."""

        participant_links = tuple(session.participant_links)
        with self._database.transaction() as connection:
            upsert_session(connection, session)
            replace_session_participants(
                connection,
                session_id=session.id,
                participant_links=participant_links,
            )
        return self._rebuild_session(session, participant_links)

    def get_by_id(self, session_id: str) -> MeetingSession | None:
        """세션 ID로 세션을 조회한다."""

        with self._database.transaction() as connection:
            row = fetch_session_row(connection, session_id)
            if row is None:
                return None
            participant_links = self._list_session_participants(connection, session_id)
        return self._build_session_from_row(row, participant_links)

    def delete(self, session_id: str) -> bool:
        """세션과 cascade 연결 데이터를 함께 삭제한다."""

        with self._database.transaction() as connection:
            return delete_session_row(connection, session_id)

    def list_running(self, *, limit: int = 500) -> list[MeetingSession]:
        """실행 중인 세션 목록을 조회한다."""

        with self._database.transaction() as connection:
            rows = fetch_running_session_rows(connection, limit=limit)
            sessions: list[MeetingSession] = []
            for row in rows:
                participant_links = self._list_session_participants(connection, row["id"])
                sessions.append(self._build_session_from_row(row, participant_links))
        return sessions

    def mark_recovery_required_if_running(
        self,
        session_id: str,
        *,
        recovery_reason: str,
        recovery_detected_at: str,
    ) -> MeetingSession | None:
        """실행 중인 세션만 복구 필요 상태로 전이한다."""

        with self._database.transaction() as connection:
            row = mark_session_recovery_required_if_running(
                connection,
                session_id=session_id,
                recovery_reason=recovery_reason,
                recovery_detected_at=recovery_detected_at,
            )
            if row is None:
                return None
            participant_links = self._list_session_participants(connection, session_id)
        return self._build_session_from_row(row, participant_links)

    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
        """세션의 실제 활성 입력 소스를 갱신한다."""

        session = self.get_by_id(session_id)
        if session is None:
            return None
        updated_session = session.mark_active_source(input_source)
        if updated_session is session:
            return session
        return self.save(updated_session)

    def list_recent(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 50,
    ) -> list[MeetingSession]:
        """조건에 맞는 최근 세션 목록을 조회한다."""

        with self._database.transaction() as connection:
            rows = fetch_recent_session_rows(
                connection,
                created_by_user_id=created_by_user_id,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                limit=limit,
            )
            sessions: list[MeetingSession] = []
            for row in rows:
                participant_links = self._list_session_participants(connection, row["id"])
                sessions.append(self._build_session_from_row(row, participant_links))
        return sessions

    def count_running(self) -> int:
        """실행 중 세션 수를 반환한다."""

        with self._database.transaction() as connection:
            return fetch_running_session_count(connection)

    def count_running_filtered(
        self,
        *,
        created_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        """조건에 맞는 진행 중 세션 수를 반환한다."""

        with self._database.transaction() as connection:
            return fetch_running_session_count_filtered(
                connection,
                created_by_user_id=created_by_user_id,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
            )

    def _build_session_from_row(
        self,
        row,
        participant_links: tuple[SessionParticipant, ...],
    ) -> MeetingSession:
        """기존 내부 API 호환용 wrapper."""

        return build_session_from_row(row, participant_links)

    def _rebuild_session(
        self,
        session: MeetingSession,
        participant_links: tuple[SessionParticipant, ...],
    ) -> MeetingSession:
        """기존 내부 API 호환용 wrapper."""

        return rebuild_session(session, participant_links)

    @staticmethod
    def _list_session_participants(connection, session_id: str) -> tuple[SessionParticipant, ...]:
        """기존 내부 API 호환용 wrapper."""

        return list_session_participants(connection, session_id)
