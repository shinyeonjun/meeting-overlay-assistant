"""SQLite 발화 저장소 구현."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import replace

from server.app.domain.models.utterance import Utterance
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.repositories.contracts.utterance_repository import UtteranceRepository


class SQLiteUtteranceRepository(UtteranceRepository):
    """SQLite 기반 발화 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(
        self,
        utterance: Utterance,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> Utterance:
        with self._connection_scope(connection) as active_connection:
            current = utterance
            for _ in range(3):
                try:
                    active_connection.execute(
                        """
                        INSERT INTO utterances (
                            id, session_id, seq_num, start_ms, end_ms, text, confidence, input_source, stt_backend, latency_ms
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            current.id,
                            current.session_id,
                            current.seq_num,
                            current.start_ms,
                            current.end_ms,
                            current.text,
                            current.confidence,
                            current.input_source,
                            current.stt_backend,
                            current.latency_ms,
                        ),
                    )
                    return current
                except sqlite3.IntegrityError as error:
                    if not self._is_sequence_unique_error(error):
                        raise
                    next_seq = self.next_sequence(
                        current.session_id,
                        connection=active_connection,
                    )
                    current = replace(current, seq_num=next_seq)
            raise sqlite3.IntegrityError(
                "utterances(session_id, seq_num) 유니크 제약 충돌 재시도 초과"
            )

    def next_sequence(
        self,
        session_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> int:
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(
                "SELECT COALESCE(MAX(seq_num), 0) AS max_seq FROM utterances WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["max_seq"]) + 1

    def list_by_session(
        self,
        session_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> list[Utterance]:
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                """
                SELECT * FROM utterances
                WHERE session_id = ?
                ORDER BY seq_num ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            Utterance(
                id=row["id"],
                session_id=row["session_id"],
                seq_num=row["seq_num"],
                start_ms=row["start_ms"],
                end_ms=row["end_ms"],
                text=row["text"],
                confidence=row["confidence"],
                input_source=row["input_source"],
                stt_backend=row["stt_backend"],
                latency_ms=row["latency_ms"],
            )
            for row in rows
        ]

    def list_recent_by_session(
        self,
        session_id: str,
        limit: int,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> list[Utterance]:
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                """
                SELECT * FROM utterances
                WHERE session_id = ?
                ORDER BY seq_num DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        recent_rows = list(reversed(rows))
        return [
            Utterance(
                id=row["id"],
                session_id=row["session_id"],
                seq_num=row["seq_num"],
                start_ms=row["start_ms"],
                end_ms=row["end_ms"],
                text=row["text"],
                confidence=row["confidence"],
                input_source=row["input_source"],
                stt_backend=row["stt_backend"],
                latency_ms=row["latency_ms"],
            )
            for row in recent_rows
        ]

    @contextmanager
    def _connection_scope(self, connection: sqlite3.Connection | None):
        if connection is not None:
            yield connection
            return
        with self._database.transaction() as managed_connection:
            yield managed_connection

    @staticmethod
    def _is_sequence_unique_error(error: sqlite3.IntegrityError) -> bool:
        message = str(error).lower()
        return (
            "unique constraint failed" in message
            and "utterances.session_id" in message
            and "utterances.seq_num" in message
        )
