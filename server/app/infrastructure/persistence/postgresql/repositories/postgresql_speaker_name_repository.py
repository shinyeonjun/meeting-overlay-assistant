"""PostgreSQL 세션 화자 이름 저장소 구현."""

from __future__ import annotations

from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
)
from server.app.repositories.contracts.speaker_name_repository import SpeakerNameRepository


class PostgreSQLSpeakerNameRepository(PostgreSQLRepositoryBase, SpeakerNameRepository):
    """PostgreSQL 기반 화자 이름 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        super().__init__(database)

    def list_by_session(
        self,
        session_id: str,
        *,
        transcript_version: int,
        connection=None,
    ) -> dict[str, str]:
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                """
                SELECT speaker_label, display_name
                FROM session_speaker_names
                WHERE session_id = %s AND transcript_version = %s
                """,
                (session_id, transcript_version),
            ).fetchall()
        return {str(row["speaker_label"]): str(row["display_name"]) for row in rows}

    def set_name(
        self,
        session_id: str,
        speaker_label: str,
        display_name: str,
        *,
        transcript_version: int,
        connection=None,
    ) -> None:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                """
                INSERT INTO session_speaker_names (
                    session_id, speaker_label, display_name, transcript_version, updated_at
                )
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (session_id, speaker_label) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    transcript_version = EXCLUDED.transcript_version,
                    updated_at = NOW()
                """,
                (session_id, speaker_label, display_name, transcript_version),
            )

    def clear_name(
        self,
        session_id: str,
        speaker_label: str,
        *,
        connection=None,
    ) -> None:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                """
                DELETE FROM session_speaker_names
                WHERE session_id = %s AND speaker_label = %s
                """,
                (session_id, speaker_label),
            )
