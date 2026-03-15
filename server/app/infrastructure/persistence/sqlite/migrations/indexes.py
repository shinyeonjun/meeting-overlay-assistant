"""SQLite 보조 인덱스 마이그레이션."""

from __future__ import annotations

import sqlite3


def ensure_additional_indexes(connection: sqlite3.Connection) -> None:
    """기능 보강 후 필요한 인덱스를 준비한다."""

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
        CREATE INDEX IF NOT EXISTS idx_reports_generated_by_user
        ON reports(generated_by_user_id, generated_at)
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
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_status_started
        ON sessions(status, started_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_created_by_user
        ON sessions(created_by_user_id, started_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_account_started
        ON sessions(account_id, started_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_contact_started
        ON sessions(contact_id, started_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_context_thread_started
        ON sessions(context_thread_id, started_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_accounts_workspace_name
        ON accounts(workspace_id, name)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_workspace_account_name
        ON contacts(workspace_id, account_id, name)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_context_threads_workspace_updated
        ON context_threads(workspace_id, updated_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_members_user_status
        ON workspace_members(user_id, status)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_members_role
        ON workspace_members(workspace_id, workspace_role, status)
        """
    )
