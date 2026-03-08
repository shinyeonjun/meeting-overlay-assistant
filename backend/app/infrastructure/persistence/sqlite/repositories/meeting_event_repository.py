"""SQLite 회의 이벤트 저장소 구현."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.shared.enums import EventPriority, EventState, EventType
from backend.app.infrastructure.persistence.sqlite.database import Database
from backend.app.repositories.contracts.meeting_event_repository import MeetingEventRepository


class SQLiteMeetingEventRepository(MeetingEventRepository):
    """SQLite 기반 회의 이벤트 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(
        self,
        event: MeetingEvent,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                """
                INSERT INTO overlay_events (
                    id, session_id, source_utterance_id, source_screen_id, event_type,
                    title, normalized_title, body, evidence_text, speaker_label, state, priority, assignee, due_date, topic_group, input_source, insight_scope,
                    created_at_ms, updated_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.session_id,
                    event.source_utterance_id,
                    event.source_screen_id,
                    event.event_type.value,
                    event.title,
                    event.normalized_title,
                    event.body,
                    event.evidence_text,
                    event.speaker_label,
                    event.state.value,
                    int(event.priority),
                    event.assignee,
                    event.due_date,
                    event.topic_group,
                    event.input_source,
                    event.insight_scope,
                    event.created_at_ms,
                    event.updated_at_ms,
                ),
            )
        return event

    def update(
        self,
        event: MeetingEvent,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                """
                UPDATE overlay_events
                SET source_utterance_id = ?,
                    source_screen_id = ?,
                    event_type = ?,
                    title = ?,
                    normalized_title = ?,
                    body = ?,
                    evidence_text = ?,
                    speaker_label = ?,
                    state = ?,
                    priority = ?,
                    assignee = ?,
                    due_date = ?,
                    topic_group = ?,
                    input_source = ?,
                    insight_scope = ?,
                    created_at_ms = ?,
                    updated_at_ms = ?
                WHERE id = ?
                """,
                (
                    event.source_utterance_id,
                    event.source_screen_id,
                    event.event_type.value,
                    event.title,
                    event.normalized_title,
                    event.body,
                    event.evidence_text,
                    event.speaker_label,
                    event.state.value,
                    int(event.priority),
                    event.assignee,
                    event.due_date,
                    event.topic_group,
                    event.input_source,
                    event.insight_scope,
                    event.created_at_ms,
                    event.updated_at_ms,
                    event.id,
                ),
            )
        return event

    def list_by_session(
        self,
        session_id: str,
        *,
        insight_scope: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[MeetingEvent]:
        query = """
            SELECT * FROM overlay_events
            WHERE session_id = ?
        """
        params: list[str] = [session_id]
        if insight_scope is not None:
            query += " AND insight_scope = ?"
            params.append(insight_scope)
        query += " ORDER BY created_at_ms ASC"
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                query,
                tuple(params),
            ).fetchall()
        return [self._to_event(row) for row in rows]

    def get_by_id(
        self,
        event_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> MeetingEvent | None:
        with self._connection_scope(connection) as active_connection:
            row = active_connection.execute(
                """
                SELECT * FROM overlay_events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
        return self._to_event(row) if row is not None else None

    def find_merge_target(
        self,
        candidate: MeetingEvent,
        *,
        connection: sqlite3.Connection | None = None,
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
        connection: sqlite3.Connection | None = None,
    ) -> list[MeetingEvent]:
        query = """
            SELECT * FROM overlay_events
            WHERE session_id = ?
              AND source_utterance_id = ?
        """
        params: list[str] = [session_id, source_utterance_id]
        if insight_scope is not None:
            query += " AND insight_scope = ?"
            params.append(insight_scope)
        query += " ORDER BY created_at_ms ASC"
        with self._connection_scope(connection) as active_connection:
            rows = active_connection.execute(
                query,
                tuple(params),
            ).fetchall()
        return [self._to_event(row) for row in rows]

    def delete(
        self,
        event_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        with self._connection_scope(connection) as active_connection:
            active_connection.execute(
                "DELETE FROM overlay_events WHERE id = ?",
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
            """
            SELECT * FROM overlay_events
            WHERE session_id = ?
              AND event_type = ?
              AND normalized_title = ?
              AND insight_scope = ?
              AND state != ?
            ORDER BY updated_at_ms DESC
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

    def _to_event(self, row: sqlite3.Row) -> MeetingEvent:
        return MeetingEvent(
            id=row["id"],
            session_id=row["session_id"],
            event_type=EventType(row["event_type"]),
            title=row["title"],
            body=row["body"],
            evidence_text=row["evidence_text"],
            speaker_label=row["speaker_label"],
            state=EventState(row["state"]),
            priority=EventPriority(row["priority"]),
            topic_group=row["topic_group"],
            source_utterance_id=row["source_utterance_id"],
            assignee=row["assignee"],
            due_date=row["due_date"],
            source_screen_id=row["source_screen_id"],
            created_at_ms=row["created_at_ms"],
            updated_at_ms=row["updated_at_ms"],
            input_source=row["input_source"],
            insight_scope=row["insight_scope"],
        )

    @contextmanager
    def _connection_scope(self, connection: sqlite3.Connection | None):
        if connection is not None:
            yield connection
            return
        with self._database.transaction() as managed_connection:
            yield managed_connection
