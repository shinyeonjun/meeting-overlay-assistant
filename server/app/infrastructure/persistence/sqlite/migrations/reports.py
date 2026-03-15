"""리포트 공유 관련 SQLite 마이그레이션."""

from __future__ import annotations

import sqlite3

from server.app.infrastructure.persistence.sqlite.migrations.common import get_table_columns


def migrate_report_version(connection: sqlite3.Connection) -> None:
    """리포트 버전 컬럼과 유니크 인덱스를 보강한다."""

    columns = get_table_columns(connection, "reports")
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


def migrate_report_insight_source(connection: sqlite3.Connection) -> None:
    """리포트 인사이트 출처 컬럼을 보강한다."""

    columns = get_table_columns(connection, "reports")
    if "insight_source" not in columns:
        connection.execute(
            "ALTER TABLE reports ADD COLUMN insight_source TEXT NOT NULL DEFAULT 'live_fallback'"
        )


def migrate_report_generated_by_user(connection: sqlite3.Connection) -> None:
    """리포트 생성 사용자 컬럼을 보강한다."""

    columns = get_table_columns(connection, "reports")
    if "generated_by_user_id" not in columns:
        connection.execute("ALTER TABLE reports ADD COLUMN generated_by_user_id TEXT")


def migrate_report_shares(connection: sqlite3.Connection) -> None:
    """리포트 공유 테이블을 준비한다."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS report_shares (
            id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL,
            shared_by_user_id TEXT NOT NULL,
            shared_with_user_id TEXT NOT NULL,
            permission TEXT NOT NULL DEFAULT 'view',
            note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE,
            FOREIGN KEY(shared_by_user_id) REFERENCES users(id),
            FOREIGN KEY(shared_with_user_id) REFERENCES users(id)
        )
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_report_shares_report_recipient
        ON report_shares(report_id, shared_with_user_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_report_shares_report_created
        ON report_shares(report_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_report_shares_recipient_created
        ON report_shares(shared_with_user_id, created_at)
        """
    )


def migrate_report_generation_jobs(connection: sqlite3.Connection) -> None:
    """리포트 생성 job 테이블과 인덱스를 준비한다."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS report_generation_jobs (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            status TEXT NOT NULL,
            recording_path TEXT,
            transcript_path TEXT,
            markdown_report_id TEXT,
            pdf_report_id TEXT,
            error_message TEXT,
            requested_by_user_id TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(markdown_report_id) REFERENCES reports(id) ON DELETE SET NULL,
            FOREIGN KEY(pdf_report_id) REFERENCES reports(id) ON DELETE SET NULL,
            FOREIGN KEY(requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_session_created
        ON report_generation_jobs(session_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_status_created
        ON report_generation_jobs(status, created_at)
        """
    )
