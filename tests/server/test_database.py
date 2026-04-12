"""데이터베이스 설정 테스트."""

import sqlite3

from server.app.infrastructure.persistence.sqlite.database import Database


class TestDatabase:
    """SQLite 연결 설정을 검증한다."""

    def test_sqlite_연결에서_foreign_keys가_활성화된다(self, isolated_database):
        with isolated_database.connect() as connection:
            row = connection.execute("PRAGMA foreign_keys").fetchone()

        assert row[0] == 1

    def test_구버전_sessions와_reports_테이블도_initialize로_마이그레이션된다(self, temp_database_path):
        connection = sqlite3.connect(temp_database_path)
        connection.executescript(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                mode TEXT NOT NULL,
                source TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL
            );

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
            session_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(sessions)").fetchall()
            }
            session_participant_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(session_participants)").fetchall()
            }
            participant_followup_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(participant_followups)").fetchall()
            }
            account_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
            }
            contact_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(contacts)").fetchall()
            }
            context_thread_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(context_threads)").fetchall()
            }
            report_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(reports)").fetchall()
            }
            report_job_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(report_generation_jobs)").fetchall()
            }
            event_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(overlay_events)").fetchall()
            }
            indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(reports)").fetchall()
            }
            report_job_indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(report_generation_jobs)").fetchall()
            }
            session_indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(sessions)").fetchall()
            }
            session_participant_indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(session_participants)").fetchall()
            }
            participant_followup_indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(participant_followups)").fetchall()
            }
            account_indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(accounts)").fetchall()
            }

        assert "created_by_user_id" in session_columns
        assert "account_id" in session_columns
        assert "contact_id" in session_columns
        assert "context_thread_id" in session_columns
        assert "primary_input_source" in session_columns
        assert "actual_active_sources" in session_columns
        assert "participant_name" in session_participant_columns
        assert "normalized_participant_name" in session_participant_columns
        assert "participant_email" in session_participant_columns
        assert "participant_job_title" in session_participant_columns
        assert "participant_department" in session_participant_columns
        assert "resolution_status" in session_participant_columns
        assert "contact_id" in session_participant_columns
        assert "resolution_status" in participant_followup_columns
        assert "followup_status" in participant_followup_columns
        assert "matched_contact_count" in participant_followup_columns
        assert "workspace_id" in account_columns
        assert "account_id" in contact_columns
        assert "department" in contact_columns
        assert "contact_id" in context_thread_columns
        assert "version" in report_columns
        assert "insight_source" in report_columns
        assert "generated_by_user_id" in report_columns
        assert "status" in report_job_columns
        assert "recording_path" in report_job_columns
        assert "transcript_path" in report_job_columns
        assert "markdown_report_id" in report_job_columns
        assert "pdf_report_id" in report_job_columns
        assert "insight_scope" in event_columns
        assert "uq_reports_session_type_version" in indexes
        assert "idx_reports_generated_by_user" in indexes
        assert "idx_report_generation_jobs_session_created" in report_job_indexes
        assert "idx_report_generation_jobs_status_created" in report_job_indexes
        assert "idx_sessions_created_by_user" in session_indexes
        assert "idx_sessions_account_started" in session_indexes
        assert "idx_session_participants_contact" in session_participant_indexes
        assert "idx_session_participants_account_normalized_name" in session_participant_indexes
        assert "idx_session_participants_resolution_status" in session_participant_indexes
        assert "idx_participant_followups_session_status" in participant_followup_indexes
        assert "idx_participant_followups_status_created" in participant_followup_indexes
        assert "idx_accounts_workspace_name" in account_indexes

    def test_기존_users가_기본_워크스페이스_멤버십으로_백필된다(self, temp_database_path):
        connection = sqlite3.connect(temp_database_path)
        connection.executescript(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                login_id TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                job_title TEXT,
                department TEXT,
                role TEXT NOT NULL DEFAULT 'member',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            INSERT INTO users (
                id, login_id, display_name, job_title, department, role, status, created_at, updated_at
            )
            VALUES (
                'user-1',
                'member',
                '멤버',
                '대리',
                '영업팀',
                'member',
                'active',
                '2026-03-13T00:00:00+00:00',
                '2026-03-13T00:00:00+00:00'
            );
            """
        )
        connection.commit()
        connection.close()

        database = Database(temp_database_path)
        database.initialize()

        with database.connect() as connection:
            workspace_row = connection.execute(
                "SELECT id, slug, name, status FROM workspaces WHERE id = 'workspace-default'"
            ).fetchone()
            membership_row = connection.execute(
                """
                SELECT workspace_id, user_id, workspace_role, status
                FROM workspace_members
                WHERE user_id = 'user-1'
                """
            ).fetchone()

        assert workspace_row is not None
        assert workspace_row["slug"] == "default"
        assert workspace_row["name"] == "기본 워크스페이스"
        assert membership_row is not None
        assert membership_row["workspace_id"] == "workspace-default"
        assert membership_row["workspace_role"] == "member"
        assert membership_row["status"] == "active"
