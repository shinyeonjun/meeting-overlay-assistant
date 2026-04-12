"""PostgreSQL 세션 저장소 구현."""

from __future__ import annotations

from server.app.domain.participation import SessionParticipant
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    parse_string_array,
)
from server.app.repositories.contracts.session import SessionRepository


class PostgreSQLSessionRepository(SessionRepository):
    """PostgreSQL 기반 세션 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def save(self, session: MeetingSession) -> MeetingSession:
        participant_links = tuple(session.participant_links)

        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id,
                    title,
                    mode,
                    created_by_user_id,
                    account_id,
                    contact_id,
                    context_thread_id,
                    primary_input_source,
                    actual_active_sources,
                    started_at,
                    ended_at,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    mode = EXCLUDED.mode,
                    created_by_user_id = EXCLUDED.created_by_user_id,
                    account_id = EXCLUDED.account_id,
                    contact_id = EXCLUDED.contact_id,
                    context_thread_id = EXCLUDED.context_thread_id,
                    primary_input_source = EXCLUDED.primary_input_source,
                    actual_active_sources = EXCLUDED.actual_active_sources,
                    started_at = EXCLUDED.started_at,
                    ended_at = EXCLUDED.ended_at,
                    status = EXCLUDED.status
                """,
                (
                    session.id,
                    session.title,
                    session.mode.value,
                    session.created_by_user_id,
                    session.account_id,
                    session.contact_id,
                    session.context_thread_id,
                    session.primary_input_source,
                    list(session.actual_active_sources),
                    session.started_at,
                    session.ended_at,
                    session.status.value,
                ),
            )
            connection.execute(
                "DELETE FROM session_participants WHERE session_id = %s",
                (session.id,),
            )
            for index, participant in enumerate(participant_links):
                connection.execute(
                    """
                    INSERT INTO session_participants (
                        session_id,
                        participant_order,
                        participant_name,
                        normalized_participant_name,
                        participant_email,
                        participant_job_title,
                        participant_department,
                        resolution_status,
                        contact_id,
                        account_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session.id,
                        index,
                        participant.name,
                        participant.normalized_name,
                        participant.email,
                        participant.job_title,
                        participant.department,
                        participant.resolution_status,
                        participant.contact_id,
                        participant.account_id,
                    ),
                )
        return self._rebuild_session(session, participant_links)

    def get_by_id(self, session_id: str) -> MeetingSession | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = %s",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            participant_links = self._list_session_participants(connection, session_id)
        return self._build_session_from_row(row, participant_links)

    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
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
        query = "SELECT * FROM sessions"
        params: list[object] = []
        conditions: list[str] = []

        if created_by_user_id is not None:
            conditions.append("created_by_user_id = %s")
            params.append(created_by_user_id)
        if account_id is not None:
            conditions.append("account_id = %s")
            params.append(account_id)
        if contact_id is not None:
            conditions.append("contact_id = %s")
            params.append(contact_id)
        if context_thread_id is not None:
            conditions.append("context_thread_id = %s")
            params.append(context_thread_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY started_at DESC NULLS LAST LIMIT %s"
        params.append(limit)

        with self._database.transaction() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
            sessions: list[MeetingSession] = []
            for row in rows:
                participant_links = self._list_session_participants(connection, row["id"])
                sessions.append(self._build_session_from_row(row, participant_links))
        return sessions

    def count_running(self) -> int:
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE status = %s",
                (SessionStatus.RUNNING.value,),
            ).fetchone()
        return int(row["total"]) if row is not None else 0

    def _build_session_from_row(
        self,
        row,
        participant_links: tuple[SessionParticipant, ...],
    ) -> MeetingSession:
        return MeetingSession(
            id=row["id"],
            title=row["title"],
            mode=SessionMode(row["mode"]),
            primary_input_source=row["primary_input_source"] or AudioSource.SYSTEM_AUDIO.value,
            status=SessionStatus(row["status"]),
            started_at=row["started_at"],
            created_by_user_id=row["created_by_user_id"],
            account_id=row["account_id"],
            contact_id=row["contact_id"],
            context_thread_id=row["context_thread_id"],
            ended_at=row["ended_at"],
            actual_active_sources=tuple(parse_string_array(row["actual_active_sources"])),
            participant_links=participant_links,
        )

    def _rebuild_session(
        self,
        session: MeetingSession,
        participant_links: tuple[SessionParticipant, ...],
    ) -> MeetingSession:
        return MeetingSession(
            id=session.id,
            title=session.title,
            mode=session.mode,
            primary_input_source=session.primary_input_source,
            status=session.status,
            started_at=session.started_at,
            created_by_user_id=session.created_by_user_id,
            account_id=session.account_id,
            contact_id=session.contact_id,
            context_thread_id=session.context_thread_id,
            ended_at=session.ended_at,
            actual_active_sources=session.actual_active_sources,
            participant_links=participant_links,
        )

    @staticmethod
    def _list_session_participants(connection, session_id: str) -> tuple[SessionParticipant, ...]:
        rows = connection.execute(
            """
            SELECT
                participant_name,
                normalized_participant_name,
                participant_email,
                participant_job_title,
                participant_department,
                resolution_status,
                contact_id,
                account_id
            FROM session_participants
            WHERE session_id = %s
            ORDER BY participant_order ASC
            """,
            (session_id,),
        ).fetchall()
        return tuple(
            SessionParticipant(
                name=row["participant_name"],
                normalized_name=row["normalized_participant_name"],
                email=row["participant_email"],
                job_title=row["participant_job_title"],
                department=row["participant_department"],
                resolution_status=row["resolution_status"],
                contact_id=row["contact_id"],
                account_id=row["account_id"],
            )
            for row in rows
        )
