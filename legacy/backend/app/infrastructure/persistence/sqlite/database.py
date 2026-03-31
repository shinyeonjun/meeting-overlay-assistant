"""SQLite 연결 및 초기화."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from backend.app.core.config import settings
from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.infrastructure.persistence.sqlite.schema import SCHEMA_SQL


class Database:
    """SQLite 데이터베이스 접근 객체."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @property
    def database_path(self) -> Path:
        """데이터베이스 파일 경로를 반환한다."""
        return self._database_path

    def initialize(self) -> None:
        """필수 테이블과 보조 인덱스를 준비한다."""
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            self._migrate_session_source_tracking_columns(connection)
            self._migrate_overlay_event_normalized_title(connection)
            self._migrate_overlay_event_speaker_label(connection)
            self._migrate_overlay_event_evidence_text(connection)
            self._migrate_overlay_event_insight_scope(connection)
            self._migrate_utterance_input_source(connection)
            self._migrate_utterance_stt_metrics_columns(connection)
            self._migrate_overlay_event_input_source(connection)
            self._migrate_report_snapshot_markdown(connection)
            self._migrate_report_version(connection)
            self._migrate_report_insight_source(connection)
            self._migrate_utterance_sequence_uniqueness(connection)
            self._ensure_additional_indexes(connection)
            connection.commit()

    def connect(self) -> sqlite3.Connection:
        """새 SQLite 연결을 만든다."""
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self):
        """하나의 트랜잭션 범위를 제공한다."""
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate_overlay_event_normalized_title(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
        }
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

    def _migrate_overlay_event_speaker_label(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
        }
        if "speaker_label" not in columns:
            connection.execute("ALTER TABLE overlay_events ADD COLUMN speaker_label TEXT")

    def _migrate_overlay_event_evidence_text(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
        }
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

    def _migrate_overlay_event_insight_scope(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
        }
        if "insight_scope" not in columns:
            connection.execute(
                "ALTER TABLE overlay_events ADD COLUMN insight_scope TEXT NOT NULL DEFAULT 'live'"
            )

    def _migrate_session_source_tracking_columns(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
        }
        if "primary_input_source" not in columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN primary_input_source TEXT")
        if "actual_active_sources" not in columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN actual_active_sources TEXT")

        connection.execute(
            """
            UPDATE sessions
            SET primary_input_source = source
            WHERE primary_input_source IS NULL OR primary_input_source = ''
            """
        )
        connection.execute(
            """
            UPDATE sessions
            SET actual_active_sources = '[]'
            WHERE actual_active_sources IS NULL OR actual_active_sources = ''
            """
        )

    def _migrate_utterance_input_source(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(utterances)").fetchall()
        }
        if "input_source" not in columns:
            connection.execute("ALTER TABLE utterances ADD COLUMN input_source TEXT")

    def _migrate_utterance_stt_metrics_columns(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(utterances)").fetchall()
        }
        if "stt_backend" not in columns:
            connection.execute("ALTER TABLE utterances ADD COLUMN stt_backend TEXT")
        if "latency_ms" not in columns:
            connection.execute("ALTER TABLE utterances ADD COLUMN latency_ms INTEGER")

    def _migrate_overlay_event_input_source(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
        }
        if "input_source" not in columns:
            connection.execute("ALTER TABLE overlay_events ADD COLUMN input_source TEXT")

    def _migrate_report_snapshot_markdown(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(reports)").fetchall()
        }
        if "snapshot_markdown" not in columns:
            connection.execute("ALTER TABLE reports ADD COLUMN snapshot_markdown TEXT")

    def _migrate_report_version(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(reports)").fetchall()
        }
        if "version" not in columns:
            connection.execute("ALTER TABLE reports ADD COLUMN version INTEGER NOT NULL DEFAULT 1")

        session_type_rows = connection.execute(
            """
            SELECT session_id, report_type
            FROM reports
            GROUP BY session_id, report_type
            """
        ).fetchall()
        for row in session_type_rows:
            reports = connection.execute(
                """
                SELECT id
                FROM reports
                WHERE session_id = ? AND report_type = ?
                ORDER BY generated_at ASC, id ASC
                """,
                (row["session_id"], row["report_type"]),
            ).fetchall()
            for version, report_row in enumerate(reports, start=1):
                connection.execute(
                    "UPDATE reports SET version = ? WHERE id = ?",
                    (version, report_row["id"]),
                )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_session_type_version
            ON reports(session_id, report_type, version)
            """
        )

    def _migrate_report_insight_source(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(reports)").fetchall()
        }
        if "insight_source" not in columns:
            connection.execute(
                "ALTER TABLE reports ADD COLUMN insight_source TEXT NOT NULL DEFAULT 'live_fallback'"
            )

    def _migrate_utterance_sequence_uniqueness(self, connection: sqlite3.Connection) -> None:
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

    def _ensure_additional_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_utterances_session_source_seq
            ON utterances(session_id, input_source, seq_num)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_utterances_session_backend_seq
            ON utterances(session_id, stt_backend, seq_num)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_overlay_events_session_created
            ON overlay_events(session_id, created_at_ms)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_overlay_events_source_utterance
            ON overlay_events(session_id, source_utterance_id, created_at_ms)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reports_session_generated
            ON reports(session_id, generated_at)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_status_started
            ON sessions(status, started_at)
            """
        )


database = Database(settings.database_path)
