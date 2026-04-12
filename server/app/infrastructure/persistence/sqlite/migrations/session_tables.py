"""세션 관련 마이그레이션."""

from __future__ import annotations

import json
import sqlite3

from server.app.domain.participation import normalize_participant_name
from server.app.infrastructure.persistence.sqlite.migrations.common import (
    get_table_columns,
)


def migrate_session_created_by_user(connection: sqlite3.Connection) -> None:
    """세션 생성 사용자 컬럼을 보강한다."""

    columns = get_table_columns(connection, "sessions")
    if "created_by_user_id" not in columns:
        connection.execute("ALTER TABLE sessions ADD COLUMN created_by_user_id TEXT")


def migrate_session_context_columns(connection: sqlite3.Connection) -> None:
    """세션 맥락 연결 컬럼을 보강한다."""

    columns = get_table_columns(connection, "sessions")
    if "account_id" not in columns:
        connection.execute("ALTER TABLE sessions ADD COLUMN account_id TEXT")
    if "contact_id" not in columns:
        connection.execute("ALTER TABLE sessions ADD COLUMN contact_id TEXT")
    if "context_thread_id" not in columns:
        connection.execute("ALTER TABLE sessions ADD COLUMN context_thread_id TEXT")


def migrate_session_source_tracking_columns(connection: sqlite3.Connection) -> None:
    """세션 입력 소스 추적 컬럼을 보강한다."""

    columns = get_table_columns(connection, "sessions")
    if "primary_input_source" not in columns:
        connection.execute("ALTER TABLE sessions ADD COLUMN primary_input_source TEXT")
    if "actual_active_sources" not in columns:
        connection.execute("ALTER TABLE sessions ADD COLUMN actual_active_sources TEXT")

    if "source" in columns:
        connection.execute(
            """
            UPDATE sessions
            SET primary_input_source = source
            WHERE primary_input_source IS NULL OR primary_input_source = ''
            """
        )
    else:
        connection.execute(
            """
            UPDATE sessions
            SET primary_input_source = 'system_audio'
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


def migrate_session_participants_table(connection: sqlite3.Connection) -> None:
    """정규화된 세션 참여자 테이블을 보강하고 기존 데이터를 옮긴다."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS session_participants (
            session_id TEXT NOT NULL,
            participant_order INTEGER NOT NULL,
            participant_name TEXT NOT NULL,
            normalized_participant_name TEXT NOT NULL DEFAULT '',
            participant_email TEXT,
            participant_job_title TEXT,
            participant_department TEXT,
            resolution_status TEXT NOT NULL DEFAULT 'unmatched',
            contact_id TEXT,
            account_id TEXT,
            PRIMARY KEY (session_id, participant_order),
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_participants_session_order
        ON session_participants(session_id, participant_order)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_participants_contact
        ON session_participants(contact_id, session_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_participants_account_normalized_name
        ON session_participants(account_id, normalized_participant_name)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_participants_resolution_status
        ON session_participants(resolution_status, session_id)
        """
    )

    columns = get_table_columns(connection, "session_participants")
    if "normalized_participant_name" not in columns:
        connection.execute(
            "ALTER TABLE session_participants ADD COLUMN normalized_participant_name TEXT NOT NULL DEFAULT ''"
        )
    if "participant_email" not in columns:
        connection.execute("ALTER TABLE session_participants ADD COLUMN participant_email TEXT")
    if "participant_job_title" not in columns:
        connection.execute("ALTER TABLE session_participants ADD COLUMN participant_job_title TEXT")
    if "participant_department" not in columns:
        connection.execute("ALTER TABLE session_participants ADD COLUMN participant_department TEXT")
    if "resolution_status" not in columns:
        connection.execute(
            "ALTER TABLE session_participants ADD COLUMN resolution_status TEXT NOT NULL DEFAULT 'unmatched'"
        )

    connection.execute(
        """
        UPDATE session_participants
        SET normalized_participant_name = participant_name
        WHERE normalized_participant_name IS NULL OR normalized_participant_name = ''
        """
    )
    connection.execute(
        """
        UPDATE session_participants
        SET resolution_status = CASE
            WHEN contact_id IS NOT NULL THEN 'linked'
            ELSE 'unmatched'
        END
        WHERE resolution_status IS NULL OR resolution_status = ''
        """
    )

    session_columns = get_table_columns(connection, "sessions")
    if "participants_json" not in session_columns:
        return

    session_rows = connection.execute(
        """
        SELECT id, account_id, participants_json
        FROM sessions
        WHERE participants_json IS NOT NULL AND participants_json != ''
        """
    ).fetchall()
    for row in session_rows:
        existing = connection.execute(
            "SELECT 1 FROM session_participants WHERE session_id = ? LIMIT 1",
            (row["id"],),
        ).fetchone()
        if existing is not None:
            continue
        try:
            participants = json.loads(row["participants_json"])
        except json.JSONDecodeError:
            participants = []
        if not isinstance(participants, list):
            participants = []

        seen: set[str] = set()
        normalized: list[str] = []
        for value in participants:
            if not isinstance(value, str):
                continue
            stripped = value.strip()
            if not stripped or stripped in seen:
                continue
            normalized.append(stripped)
            seen.add(stripped)

        for index, participant_name in enumerate(normalized):
            connection.execute(
                """
                INSERT INTO session_participants (
                    session_id,
                    participant_order,
                    participant_name,
                    normalized_participant_name,
                    participant_email,
                    participant_job_title,
                    participant_department,
                    resolution_status,
                    contact_id,
                    account_id
                )
                VALUES (?, ?, ?, ?, NULL, NULL, NULL, 'unmatched', NULL, ?)
                """,
                (
                    row["id"],
                    index,
                    participant_name,
                    normalize_participant_name(participant_name),
                    row["account_id"],
                ),
            )
