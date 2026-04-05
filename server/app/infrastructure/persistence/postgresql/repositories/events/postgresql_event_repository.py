"""PostgreSQL 이벤트 저장소 구현."""

from __future__ import annotations

from server.app.domain.events import MeetingEvent
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
)
from server.app.infrastructure.persistence.postgresql.repositories.events.helpers import (
    SELECT_COLUMNS,
    build_get_by_id_query,
    build_insert_values,
    build_list_by_session_query,
    build_list_by_source_utterance_query,
    build_merge_lookup,
    build_update_values,
    row_to_event,
)
from server.app.repositories.contracts.events.event_repository import MeetingEventRepository


class PostgreSQLMeetingEventRepository(PostgreSQLRepositoryBase, MeetingEventRepository):
    """PostgreSQL 기반 회의 이벤트 저장소."""

    _SELECT_COLUMNS = SELECT_COLUMNS

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
                    input_source, insight_scope, event_source, processing_job_id,
                    created_at, updated_at, finalized_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                build_insert_values(event),
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
                    event_source = %s,
                    processing_job_id = %s,
                    created_at = %s,
                    updated_at = %s,
                    finalized_at = %s
                WHERE id = %s
                """,
                build_update_values(event),
            )
        return event

    def list_by_session(
        self,
        session_id: str,
        *,
        insight_scope: str | None = None,
        connection=None,
    ) -> list[MeetingEvent]:
        query, params = build_list_by_session_query(
            session_id,
            insight_scope=insight_scope,
        )
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(query, params).fetchall()
        return [row_to_event(row) for row in rows]

    def get_by_id(
        self,
        event_id: str,
        *,
        connection=None,
    ) -> MeetingEvent | None:
        query, params = build_get_by_id_query(event_id)
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(query, params).fetchone()
        return row_to_event(row) if row is not None else None

    def find_merge_target(
        self,
        candidate: MeetingEvent,
        *,
        connection=None,
    ) -> MeetingEvent | None:
        query, params = build_merge_lookup(candidate)
        if query is None:
            return None
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(query, params).fetchone()
        return row_to_event(row) if row is not None else None

    def list_by_source_utterance(
        self,
        session_id: str,
        source_utterance_id: str,
        *,
        insight_scope: str | None = None,
        connection=None,
    ) -> list[MeetingEvent]:
        query, params = build_list_by_source_utterance_query(
            session_id,
            source_utterance_id,
            insight_scope=insight_scope,
        )
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(query, params).fetchall()
        return [row_to_event(row) for row in rows]

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

    def delete_by_session(
        self,
        session_id: str,
        *,
        connection=None,
    ) -> int:
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                """
                DELETE FROM overlay_events
                WHERE session_id = %s
                RETURNING 1
                """,
                (session_id,),
            ).fetchall()
        return len(rows)

    @staticmethod
    def _to_event(row) -> MeetingEvent:
        return row_to_event(row)
