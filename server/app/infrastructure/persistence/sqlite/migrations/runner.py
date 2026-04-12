"""SQLite 마이그레이션 실행 순서."""

from __future__ import annotations

import sqlite3

from server.app.infrastructure.persistence.sqlite.migrations.context import (
    migrate_meeting_context_tables,
    migrate_workspaces_and_memberships,
)
from server.app.infrastructure.persistence.sqlite.migrations.events import (
    migrate_overlay_event_evidence_text,
    migrate_overlay_event_input_source,
    migrate_overlay_event_insight_scope,
    migrate_overlay_event_normalized_title,
    migrate_overlay_event_speaker_label,
    migrate_utterance_input_source,
    migrate_utterance_sequence_uniqueness,
    migrate_utterance_stt_metrics_columns,
)
from server.app.infrastructure.persistence.sqlite.migrations.indexes import (
    ensure_additional_indexes,
)
from server.app.infrastructure.persistence.sqlite.migrations.participation_tables import (
    migrate_participant_followups_table,
)
from server.app.infrastructure.persistence.sqlite.migrations.reports import (
    migrate_report_generated_by_user,
    migrate_report_generation_jobs,
    migrate_report_insight_source,
    migrate_report_shares,
    migrate_report_version,
)
from server.app.infrastructure.persistence.sqlite.migrations.session_tables import (
    migrate_session_context_columns,
    migrate_session_created_by_user,
    migrate_session_participants_table,
    migrate_session_source_tracking_columns,
)


def run_sqlite_migrations(connection: sqlite3.Connection) -> None:
    """현재 SQLite 스키마를 최신 형태로 맞춘다."""

    migrate_meeting_context_tables(connection)
    migrate_workspaces_and_memberships(connection)
    migrate_session_created_by_user(connection)
    migrate_session_context_columns(connection)
    migrate_session_source_tracking_columns(connection)
    migrate_session_participants_table(connection)
    migrate_participant_followups_table(connection)
    migrate_overlay_event_normalized_title(connection)
    migrate_overlay_event_speaker_label(connection)
    migrate_overlay_event_evidence_text(connection)
    migrate_overlay_event_insight_scope(connection)
    migrate_utterance_input_source(connection)
    migrate_utterance_stt_metrics_columns(connection)
    migrate_overlay_event_input_source(connection)
    migrate_report_version(connection)
    migrate_report_insight_source(connection)
    migrate_report_generated_by_user(connection)
    migrate_report_shares(connection)
    migrate_report_generation_jobs(connection)
    migrate_utterance_sequence_uniqueness(connection)
    ensure_additional_indexes(connection)
