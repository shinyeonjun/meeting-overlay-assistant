"""PostgreSQL 이벤트 저장소 구현."""

from __future__ import annotations

from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
    epoch_ms_to_timestamptz,
    timestamptz_to_epoch_ms,
)
from server.app.repositories.contracts.events.event_repository import MeetingEventRepository


class PostgreSQLMeetingEventRepository(PostgreSQLRepositoryBase, MeetingEventRepository):
    """PostgreSQL 기반 회의 이벤트 저장소."""

    _SELECT_COLUMNS = """
        SELECT
            id,
            session_id,
            source_utterance_id,
            event_type,
            title,
            normalized_title,
            body,
            evidence_text,
            speaker_label,
            state,
            input_source,
            insight_scope,
            CAST(EXTRACT(EPOCH FROM created_at) * 1000 AS BIGINT) AS created_at_ms,
            CAST(EXTRACT(EPOCH FROM updated_at) * 1000 AS BIGINT) AS updated_at_ms
        FROM overlay_events
    """

    def __init__(self, database: PostgreSQLDatabase) -> None:
        super().__init__(database)

    def save(
        self,
        event: MeetingEvent,
        *,
        connection=None,
    ) -> MeetingEvent:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                """
                INSERT INTO overlay_events (
                    id, session_id, source_utterance_id, event_type,
                    title, normalized_title, body, evidence_text, speaker_label, state,
                    input_source, insight_scope,
                    created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    event.id,
                    event.session_id,
                    event.source_utterance_id,
                    event.event_type.value,
                    event.title,
                    event.normalized_title,
                    event.body,
                    event.evidence_text,
                    event.speaker_label,
                    event.state.value,
                    event.input_source,
                    event.insight_scope,
                    epoch_ms_to_timestamptz(event.created_at_ms),
                    epoch_ms_to_timestamptz(event.updated_at_ms),
                ),
            )
        return event

    def update(
        self,
        event: MeetingEvent,
        *,
        connection=None,
    ) -> MeetingEvent:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                """
                UPDATE overlay_events
                SET source_utterance_id = %s,
                    event_type = %s,
                    title = %s,
                    normalized_title = %s,
                    body = %s,
                    evidence_text = %s,
                    speaker_label = %s,
                    state = %s,
                    input_source = %s,
                    insight_scope = %s,
                    created_at = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (
                    event.source_utterance_id,
                    event.event_type.value,
                    event.title,
                    event.normalized_title,
                    event.body,
                    event.evidence_text,
                    event.speaker_label,
                    event.state.value,
                    event.input_source,
                    event.insight_scope,
                    epoch_ms_to_timestamptz(event.created_at_ms),
                    epoch_ms_to_timestamptz(event.updated_at_ms),
                    event.id,
                ),
            )
        return event

    def list_by_session(
        self,
        session_id: str,
        *,
        insight_scope: str | None = None,
        connection=None,
    ) -> list[MeetingEvent]:
        query = f"""
            {self._SELECT_COLUMNS}
            WHERE session_id = %s
        """
        params: list[object] = [session_id]
        if insight_scope is not None:
            query += " AND insight_scope = %s"
            params.append(insight_scope)
        query += " ORDER BY created_at ASC"
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(query, tuple(params)).fetchall()
        return [self._to_event(row) for row in rows]

    def get_by_id(
        self,
        event_id: str,
        *,
        connection=None,
    ) -> MeetingEvent | None:
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(
                f"""
                {self._SELECT_COLUMNS}
                WHERE id = %s
                """,
                (event_id,),
            ).fetchone()
        return self._to_event(row) if row is not None else None

    def find_merge_target(
        self,
        candidate: MeetingEvent,
        *,
        connection=None,
    ) -> MeetingEvent | None:
        query, params = self._build_merge_lookup(candidate)
        if query is None:
            return None
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(query, params).fetchone()
        return self._to_event(row) if row is not None else None

    def list_by_source_utterance(
        self,
        session_id: str,
        source_utterance_id: str,
        *,
        insight_scope: str | None = None,
        connection=None,
    ) -> list[MeetingEvent]:
        query = f"""
            {self._SELECT_COLUMNS}
            WHERE session_id = %s
              AND source_utterance_id = %s
        """
        params: list[object] = [session_id, source_utterance_id]
        if insight_scope is not None:
            query += " AND insight_scope = %s"
            params.append(insight_scope)
        query += " ORDER BY created_at ASC"
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(query, tuple(params)).fetchall()
        return [self._to_event(row) for row in rows]

    def delete(
        self,
        event_id: str,
        *,
        connection=None,
    ) -> None:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                "DELETE FROM overlay_events WHERE id = %s",
                (event_id,),
            )

    def _build_merge_lookup(self, candidate: MeetingEvent) -> tuple[str | None, tuple]:
        if candidate.event_type == EventType.TOPIC:
            return None, ()
        if candidate.event_type not in {
            EventType.QUESTION,
            EventType.DECISION,
            EventType.ACTION_ITEM,
            EventType.RISK,
        }:
            return None, ()
        return (
            f"""
            {self._SELECT_COLUMNS}
            WHERE session_id = %s
              AND event_type = %s
              AND normalized_title = %s
              AND insight_scope = %s
              AND state != %s
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (
                candidate.session_id,
                candidate.event_type.value,
                candidate.normalized_title,
                candidate.insight_scope,
                EventState.CLOSED.value,
            ),
        )

    @staticmethod
    def _to_event(row) -> MeetingEvent:
        return MeetingEvent(
            id=row["id"],
            session_id=row["session_id"],
            event_type=EventType(row["event_type"]),
            title=row["title"],
            body=row["body"],
            evidence_text=row["evidence_text"],
            speaker_label=row["speaker_label"],
            state=EventState(row["state"]),
            source_utterance_id=row["source_utterance_id"],
            created_at_ms=timestamptz_to_epoch_ms(row["created_at_ms"]),
            updated_at_ms=timestamptz_to_epoch_ms(row["updated_at_ms"]),
            input_source=row["input_source"],
            insight_scope=row["insight_scope"],
        )
