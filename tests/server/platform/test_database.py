"""PostgreSQL 스키마 설정 테스트."""

from server.app.api.http.wiring import persistence as persistence_wiring
from server.app.core.workspace_defaults import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
)
from server.app.domain.models.user import UserAccount
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_auth_repository import (
    PostgreSQLAuthRepository,
)


class TestDatabase:
    """PostgreSQL 기준 스키마와 기본 workspace 생성을 검증한다."""

    def test_postgresql_연결이_동작한다(self, isolated_database):
        with isolated_database.transaction() as connection:
            row = connection.execute("SELECT 1 AS value").fetchone()

        assert row is not None
        assert row["value"] == 1

    def test_runtime_스키마에_필수_컬럼과_인덱스가_존재한다(self, isolated_database):
        def get_columns(connection, table_name: str) -> set[str]:
            rows = connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table_name,),
            ).fetchall()
            return {row["column_name"] for row in rows}

        with isolated_database.transaction() as connection:
            session_columns = get_columns(connection, "sessions")
            session_participant_columns = get_columns(connection, "session_participants")
            participant_followup_columns = get_columns(connection, "participant_followups")
            account_columns = get_columns(connection, "accounts")
            contact_columns = get_columns(connection, "contacts")
            context_thread_columns = get_columns(connection, "context_threads")
            report_columns = get_columns(connection, "reports")
            post_processing_job_columns = get_columns(connection, "session_post_processing_jobs")
            report_job_columns = get_columns(connection, "report_generation_jobs")
            event_columns = get_columns(connection, "overlay_events")
            rows = connection.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                """
            ).fetchall()
            indexes = {row["indexname"] for row in rows}

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
        assert "file_artifact_id" in report_columns
        assert "insight_source" in report_columns
        assert "generated_by_user_id" in report_columns
        assert "status" in post_processing_job_columns
        assert "recording_artifact_id" in post_processing_job_columns
        assert "recording_path" in post_processing_job_columns
        assert "claimed_by_worker_id" in post_processing_job_columns
        assert "lease_expires_at" in post_processing_job_columns
        assert "attempt_count" in post_processing_job_columns
        assert "status" in report_job_columns
        assert "recording_artifact_id" in report_job_columns
        assert "recording_path" in report_job_columns
        assert "transcript_path" in report_job_columns
        assert "markdown_report_id" in report_job_columns
        assert "pdf_report_id" in report_job_columns
        assert "claimed_by_worker_id" in report_job_columns
        assert "lease_expires_at" in report_job_columns
        assert "attempt_count" in report_job_columns
        assert "insight_scope" in event_columns
        assert "uq_utterances_session_seq" in indexes
        assert "uq_report_shares_report_recipient" in indexes
        assert "idx_session_post_processing_jobs_session_created" in indexes
        assert "idx_session_post_processing_jobs_status_created" in indexes
        assert "idx_session_post_processing_jobs_claimable" in indexes
        assert "idx_report_generation_jobs_session_created" in indexes
        assert "idx_report_generation_jobs_status_created" in indexes
        assert "idx_report_generation_jobs_claimable" in indexes
        assert "idx_sessions_created_by_user" in indexes
        assert "idx_sessions_account_started" in indexes
        assert "idx_session_participants_contact" in indexes
        assert "idx_session_participants_account_normalized_name" in indexes
        assert "idx_session_participants_resolution_status" in indexes
        assert "idx_participant_followups_session_status" in indexes
        assert "idx_participant_followups_status_created" in indexes
        assert "idx_accounts_workspace_name" in indexes

    def test_initialize_primary_persistence가_기본_workspace를_자동_생성한다(
        self,
        isolated_database,
        monkeypatch,
    ):
        with isolated_database.transaction() as connection:
            connection.execute("DELETE FROM workspaces WHERE id = %s", (DEFAULT_WORKSPACE_ID,))

        monkeypatch.setattr(
            persistence_wiring,
            "get_postgresql_database",
            lambda: isolated_database,
        )

        persistence_wiring.initialize_primary_persistence()

        with isolated_database.transaction() as connection:
            row = connection.execute(
                "SELECT id, slug, name, status FROM workspaces WHERE id = %s",
                (DEFAULT_WORKSPACE_ID,),
            ).fetchone()

        assert row is not None
        assert row["id"] == DEFAULT_WORKSPACE_ID
        assert row["slug"] == DEFAULT_WORKSPACE_SLUG
        assert row["name"] == DEFAULT_WORKSPACE_NAME
        assert row["status"] == "active"

    def test_사용자_생성시_기본_워크스페이스와_멤버십이_생성된다(self, isolated_database):
        repository = PostgreSQLAuthRepository(isolated_database)
        user = UserAccount.create(
            login_id="member",
            display_name="멤버",
            job_title="대리",
            department="영업팀",
        )

        repository.create_user_with_password(
            user=user,
            password_hash="hashed-password",
            password_updated_at="2026-03-13T00:00:00+00:00",
        )

        with isolated_database.transaction() as connection:
            workspace_row = connection.execute(
                "SELECT id, slug, name, status FROM workspaces WHERE id = %s",
                (DEFAULT_WORKSPACE_ID,),
            ).fetchone()
            membership_row = connection.execute(
                """
                SELECT workspace_id, user_id, workspace_role, status
                FROM workspace_members
                WHERE user_id = %s
                """,
                (user.id,),
            ).fetchone()

        assert workspace_row is not None
        assert workspace_row["slug"] == DEFAULT_WORKSPACE_SLUG
        assert workspace_row["name"] == DEFAULT_WORKSPACE_NAME
        assert membership_row is not None
        assert membership_row["workspace_id"] == DEFAULT_WORKSPACE_ID
        assert membership_row["workspace_role"] == "member"
        assert membership_row["status"] == "active"
