"""발화/이벤트 관련 마이그레이션."""

from __future__ import annotations

import sqlite3

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.infrastructure.persistence.sqlite.migrations.common import (
    get_table_columns,
)


def migrate_overlay_event_normalized_title(connection: sqlite3.Connection) -> None:
    """이벤트 병합용 정규화 제목 컬럼을 보강한다."""

    columns = get_table_columns(connection, "overlay_events")
    if "normalized_title" not in columns:
        connection.execute("ALTER TABLE overlay_events ADD COLUMN normalized_title TEXT")

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_overlay_events_merge_lookup
        ON overlay_events(session_id, event_type, normalized_title, state, updated_at_ms)
        """
    )
    rows = connection.execute(
        """
        SELECT id, title
        FROM overlay_events
        WHERE normalized_title IS NULL OR normalized_title = ''
        """
    ).fetchall()
    for row in rows:
        connection.execute(
            """
            UPDATE overlay_events
            SET normalized_title = ?
            WHERE id = ?
            """,
            (MeetingEvent.normalize_title(row["title"]), row["id"]),
        )


def migrate_overlay_event_speaker_label(connection: sqlite3.Connection) -> None:
    """이벤트 화자 라벨 컬럼을 보강한다."""

    columns = get_table_columns(connection, "overlay_events")
    if "speaker_label" not in columns:
        connection.execute("ALTER TABLE overlay_events ADD COLUMN speaker_label TEXT")


def migrate_overlay_event_evidence_text(connection: sqlite3.Connection) -> None:
    """이벤트 근거 텍스트를 보강한다."""

    columns = get_table_columns(connection, "overlay_events")
    if "evidence_text" not in columns:
        connection.execute("ALTER TABLE overlay_events ADD COLUMN evidence_text TEXT")
    connection.execute(
        """
        UPDATE overlay_events
        SET evidence_text = (
            SELECT utterances.text
            FROM utterances
            WHERE utterances.id = overlay_events.source_utterance_id
        )
        WHERE (evidence_text IS NULL OR evidence_text = '')
          AND source_utterance_id IS NOT NULL
        """
    )


def migrate_overlay_event_insight_scope(connection: sqlite3.Connection) -> None:
    """이벤트 인사이트 범위 컬럼을 보강한다."""

    columns = get_table_columns(connection, "overlay_events")
    if "insight_scope" not in columns:
        connection.execute(
            "ALTER TABLE overlay_events ADD COLUMN insight_scope TEXT NOT NULL DEFAULT 'live'"
        )


def migrate_utterance_input_source(connection: sqlite3.Connection) -> None:
    """발화 입력 소스 컬럼을 보강한다."""

    columns = get_table_columns(connection, "utterances")
    if "input_source" not in columns:
        connection.execute("ALTER TABLE utterances ADD COLUMN input_source TEXT")


def migrate_utterance_stt_metrics_columns(connection: sqlite3.Connection) -> None:
    """발화 STT 메트릭 컬럼을 보강한다."""

    columns = get_table_columns(connection, "utterances")
    if "stt_backend" not in columns:
        connection.execute("ALTER TABLE utterances ADD COLUMN stt_backend TEXT")
    if "latency_ms" not in columns:
        connection.execute("ALTER TABLE utterances ADD COLUMN latency_ms INTEGER")


def migrate_overlay_event_input_source(connection: sqlite3.Connection) -> None:
    """이벤트 입력 소스 컬럼을 보강한다."""

    columns = get_table_columns(connection, "overlay_events")
    if "input_source" not in columns:
        connection.execute("ALTER TABLE overlay_events ADD COLUMN input_source TEXT")


def migrate_utterance_sequence_uniqueness(connection: sqlite3.Connection) -> None:
    """발화 순번 유니크 인덱스를 안전하게 복구한다."""

    duplicate_sessions = connection.execute(
        """
        SELECT DISTINCT session_id
        FROM utterances
        GROUP BY session_id, seq_num
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for row in duplicate_sessions:
        session_id = row["session_id"]
        utterance_rows = connection.execute(
            """
            SELECT id
            FROM utterances
            WHERE session_id = ?
            ORDER BY start_ms ASC, end_ms ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
        for new_seq, utterance_row in enumerate(utterance_rows, start=1):
            connection.execute(
                "UPDATE utterances SET seq_num = ? WHERE id = ?",
                (-new_seq, utterance_row["id"]),
            )
        for new_seq, utterance_row in enumerate(utterance_rows, start=1):
            connection.execute(
                "UPDATE utterances SET seq_num = ? WHERE id = ?",
                (new_seq, utterance_row["id"]),
            )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_utterances_session_seq
        ON utterances(session_id, seq_num)
        """
    )
