"""데이터베이스 설정 테스트."""

import sqlite3

from backend.app.infrastructure.persistence.sqlite.database import Database


class TestDatabase:
    """SQLite 연결 설정을 검증한다."""

    def test_sqlite_연결에서_foreign_keys가_활성화된다(self, isolated_database):
        with isolated_database.connect() as connection:
            row = connection.execute("PRAGMA foreign_keys").fetchone()

        assert row[0] == 1

    def test_구버전_reports_테이블도_initialize로_마이그레이션된다(self, temp_database_path):
        connection = sqlite3.connect(temp_database_path)
        connection.executescript(
            """
            CREATE TABLE reports (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                generated_at TEXT NOT NULL
            );
            """
        )
        connection.commit()
        connection.close()

        database = Database(temp_database_path)
        database.initialize()

        with database.connect() as connection:
            report_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(reports)").fetchall()
            }
            event_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
            }
            indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(reports)").fetchall()
            }

        assert "snapshot_markdown" in report_columns
        assert "version" in report_columns
        assert "insight_source" in report_columns
        assert "insight_scope" in event_columns
        assert "uq_reports_session_type_version" in indexes
