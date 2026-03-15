"""SQLite 세션 저장소 구현."""

from __future__ import annotations

import json

from server.app.domain.participation import SessionParticipant
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.repositories.contracts.session import SessionRepository


class SQLiteSessionRepository(SessionRepository):
    """SQLite 기반 세션 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, session: MeetingSession) -> MeetingSession:
        participant_links = self._resolve_participant_links(session)

        with self._database.connect() as connection:
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
                    :id,
                    :title,
                    :mode,
                    :created_by_user_id,
                    :account_id,
                    :contact_id,
                    :context_thread_id,
                    :primary_input_source,
                    :actual_active_sources,
                    :started_at,
                    :ended_at,
                    :status
                )
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    mode = excluded.mode,
                    created_by_user_id = excluded.created_by_user_id,
                    account_id = excluded.account_id,
                    contact_id = excluded.contact_id,
                    context_thread_id = excluded.context_thread_id,
                    primary_input_source = excluded.primary_input_source,
                    actual_active_sources = excluded.actual_active_sources,
                    started_at = excluded.started_at,
                    ended_at = excluded.ended_at,
                    status = excluded.status
                """,
                {
                    "id": session.id,
                    "title": session.title,
                    "mode": session.mode.value,
                    "created_by_user_id": session.created_by_user_id,
                    "account_id": session.account_id,
                    "contact_id": session.contact_id,
                    "context_thread_id": session.context_thread_id,
                    "primary_input_source": session.primary_input_source,
                    "actual_active_sources": json.dumps(
                        list(session.actual_active_sources),
                        ensure_ascii=False,
                    ),
                    "started_at": session.started_at,
                    "ended_at": session.ended_at,
                    "status": session.status.value,
                },
            )
            connection.execute(
                "DELETE FROM session_participants WHERE session_id = ?",
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            connection.commit()

        return self._rebuild_session(session, participant_links)

    def get_by_id(self, session_id: str) -> MeetingSession | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?",
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
            conditions.append("created_by_user_id = ?")
            params.append(created_by_user_id)
        if account_id is not None:
            conditions.append("account_id = ?")
            params.append(account_id)
        if contact_id is not None:
            conditions.append("contact_id = ?")
            params.append(contact_id)
        if context_thread_id is not None:
            conditions.append("context_thread_id = ?")
            params.append(context_thread_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
            session_ids = [row["id"] for row in rows]
            participant_map = self._list_session_participants_by_session_ids(connection, session_ids)

        return [
            self._build_session_from_row(row, participant_map.get(row["id"], ()))
            for row in rows
        ]

    def count_running(self) -> int:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE status = ?",
                (SessionStatus.RUNNING.value,),
            ).fetchone()
        return int(row["total"]) if row is not None else 0

    def _build_session_from_row(self, row, participant_links: tuple[SessionParticipant, ...]) -> MeetingSession:
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
            actual_active_sources=tuple(self._parse_string_array(row["actual_active_sources"])),
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

    def _resolve_participant_links(self, session: MeetingSession) -> tuple[SessionParticipant, ...]:
        return tuple(session.participant_links)

    def _list_session_participants(self, connection, session_id: str) -> tuple[SessionParticipant, ...]:
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
            WHERE session_id = ?
            ORDER BY participant_order ASC
            """,
            (session_id,),
        ).fetchall()
        return tuple(self._to_session_participant(row) for row in rows)

    def _list_session_participants_by_session_ids(
        self,
        connection,
        session_ids: list[str],
    ) -> dict[str, tuple[SessionParticipant, ...]]:
        if not session_ids:
            return {}

        placeholders = ", ".join("?" for _ in session_ids)
        rows = connection.execute(
            f"""
            SELECT
                session_id,
                participant_name,
                normalized_participant_name,
                participant_email,
                participant_job_title,
                participant_department,
                resolution_status,
                contact_id,
                account_id
            FROM session_participants
            WHERE session_id IN ({placeholders})
            ORDER BY session_id ASC, participant_order ASC
            """,
            tuple(session_ids),
        ).fetchall()

        participant_map: dict[str, list[SessionParticipant]] = {}
        for row in rows:
            participant_map.setdefault(row["session_id"], []).append(
                self._to_session_participant(row)
            )
        return {
            session_id: tuple(items)
            for session_id, items in participant_map.items()
        }

    @staticmethod
    def _to_session_participant(row) -> SessionParticipant:
        return SessionParticipant(
            name=row["participant_name"],
            normalized_name=row["normalized_participant_name"],
            contact_id=row["contact_id"],
            account_id=row["account_id"],
            email=row["participant_email"],
            job_title=row["participant_job_title"],
            department=row["participant_department"],
            resolution_status=row["resolution_status"],
        )

    @staticmethod
    def _parse_string_array(raw_value) -> list[str]:
        if raw_value in (None, ""):
            return []
        if isinstance(raw_value, list):
            return [str(item) for item in raw_value if item is not None]
        try:
            parsed = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if item is not None]
