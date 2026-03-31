"""SQLite 세션 저장소 구현."""

from __future__ import annotations

import json

from backend.app.domain.models.session import MeetingSession
from backend.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from backend.app.infrastructure.persistence.sqlite.database import Database
from backend.app.repositories.contracts.session_repository import SessionRepository


class SQLiteSessionRepository(SessionRepository):
    """SQLite 기반 세션 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, session: MeetingSession) -> MeetingSession:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, title, mode, source, primary_input_source, actual_active_sources, started_at, ended_at, status
                )
                VALUES (
                    :id, :title, :mode, :source, :primary_input_source, :actual_active_sources, :started_at, :ended_at, :status
                )
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    mode = excluded.mode,
                    source = excluded.source,
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
                    "source": session.source.value,
                    "primary_input_source": session.primary_input_source or session.source.value,
                    "actual_active_sources": json.dumps(
                        list(session.actual_active_sources),
                        ensure_ascii=False,
                    ),
                    "started_at": session.started_at,
                    "ended_at": session.ended_at,
                    "status": session.status.value,
                },
            )
            connection.commit()
        return session

    def get_by_id(self, session_id: str) -> MeetingSession | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return MeetingSession(
            id=row["id"],
            title=row["title"],
            mode=SessionMode(row["mode"]),
            source=AudioSource(row["source"]),
            status=SessionStatus(row["status"]),
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            primary_input_source=row["primary_input_source"] or row["source"],
            actual_active_sources=tuple(self._parse_active_sources(row["actual_active_sources"])),
        )

    def mark_active_source(self, session_id: str, input_source: str) -> MeetingSession | None:
        session = self.get_by_id(session_id)
        if session is None:
            return None
        updated_session = session.mark_active_source(input_source)
        if updated_session is session:
            return session
        return self.save(updated_session)

    @staticmethod
    def _parse_active_sources(raw_value: str | None) -> list[str]:
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [value for value in parsed if isinstance(value, str) and value.strip()]
