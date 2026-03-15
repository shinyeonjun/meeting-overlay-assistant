"""PostgreSQL 발화 저장소 구현."""

from __future__ import annotations

from dataclasses import replace

from server.app.domain.models.utterance import Utterance
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
)
from server.app.repositories.contracts.utterance_repository import UtteranceRepository


class PostgreSQLUtteranceRepository(PostgreSQLRepositoryBase, UtteranceRepository):
    """PostgreSQL 기반 발화 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        super().__init__(database)

    def save(
        self,
        utterance: Utterance,
        *,
        connection=None,
    ) -> Utterance:
        with self._connection_scope(connection) as active_connection:
            current = utterance
            for _ in range(3):
                try:
                    active_connection.execute(
                        """
                        INSERT INTO utterances (
                            id, session_id, seq_num, start_ms, end_ms, text, confidence,
                            input_source, stt_backend, latency_ms
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                except Exception as error:
                    if not self._is_sequence_unique_error(error):
                        raise
                    next_seq = self.next_sequence(
                        current.session_id,
                        connection=active_connection,
                    )
                    current = replace(current, seq_num=next_seq)
            raise RuntimeError("utterances(session_id, seq_num) 유니크 제약 충돌 재시도 초과")

    def next_sequence(
        self,
        session_id: str,
        *,
        connection=None,
    ) -> int:
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(
                """
                SELECT COALESCE(MAX(seq_num), 0) AS max_seq
                FROM utterances
                WHERE session_id = %s
                """,
                (session_id,),
            ).fetchone()
        return int(row["max_seq"]) + 1

    def list_by_session(
        self,
        session_id: str,
        *,
        connection=None,
    ) -> list[Utterance]:
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                """
                SELECT * FROM utterances
                WHERE session_id = %s
                ORDER BY seq_num ASC
                """,
                (session_id,),
            ).fetchall()
        return [self._to_utterance(row) for row in rows]

    def list_recent_by_session(
        self,
        session_id: str,
        limit: int,
        *,
        connection=None,
    ) -> list[Utterance]:
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                """
                SELECT * FROM utterances
                WHERE session_id = %s
                ORDER BY seq_num DESC
                LIMIT %s
                """,
                (session_id, limit),
            ).fetchall()
        return [self._to_utterance(row) for row in reversed(rows)]

    @staticmethod
    def _to_utterance(row) -> Utterance:
        return Utterance(
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

    @staticmethod
    def _is_sequence_unique_error(error: Exception) -> bool:
        sqlstate = getattr(error, "sqlstate", None)
        if sqlstate == "23505":
            return True
        return "utterances" in str(error).lower() and "seq_num" in str(error).lower()
