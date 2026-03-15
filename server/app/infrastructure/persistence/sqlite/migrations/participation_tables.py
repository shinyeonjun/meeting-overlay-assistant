"""참여자 후속 작업 마이그레이션."""

from __future__ import annotations

import sqlite3


def migrate_participant_followups_table(connection: sqlite3.Connection) -> None:
    """참여자 후속 작업 테이블과 인덱스를 준비한다."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS participant_followups (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            participant_order INTEGER NOT NULL,
            participant_name TEXT NOT NULL,
            resolution_status TEXT NOT NULL,
            followup_status TEXT NOT NULL DEFAULT 'pending',
            matched_contact_count INTEGER NOT NULL DEFAULT 0,
            contact_id TEXT,
            account_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT,
            resolved_by_user_id TEXT,
            UNIQUE(session_id, participant_order),
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE SET NULL,
            FOREIGN KEY(resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_participant_followups_session_status
        ON participant_followups(session_id, followup_status, participant_order)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_participant_followups_status_created
        ON participant_followups(followup_status, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_participant_followups_contact_status
        ON participant_followups(contact_id, followup_status)
        """
    )
