"""PostgreSQL 회의록 공유 저장소 구현."""

from __future__ import annotations

from server.app.domain.models.report_share import (
    ReceivedReportShareView,
    ReportShare,
    ReportShareView,
)
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.repositories.contracts.report_share_repository import ReportShareRepository


class PostgreSQLReportShareRepository(ReportShareRepository):
    """PostgreSQL 기반 회의록 공유 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def save(self, share: ReportShare) -> ReportShareView:
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO report_shares (
                    id,
                    report_id,
                    shared_by_user_id,
                    shared_with_user_id,
                    permission,
                    note,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    share.id,
                    share.report_id,
                    share.shared_by_user_id,
                    share.shared_with_user_id,
                    share.permission,
                    share.note,
                    share.created_at,
                ),
            )
        return self._get_view_by_id(share.id)

    def get_by_report_and_recipient(
        self,
        *,
        report_id: str,
        shared_with_user_id: str,
    ) -> ReportShare | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM report_shares
                WHERE report_id = %s AND shared_with_user_id = %s
                """,
                (report_id, shared_with_user_id),
            ).fetchone()
        if row is None:
            return None
        return ReportShare(
            id=row["id"],
            report_id=row["report_id"],
            shared_by_user_id=row["shared_by_user_id"],
            shared_with_user_id=row["shared_with_user_id"],
            permission=row["permission"],
            note=row["note"],
            created_at=row["created_at"],
        )

    def list_by_report(self, report_id: str) -> list[ReportShareView]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT
                    report_shares.id AS share_id,
                    report_shares.report_id AS report_id,
                    report_shares.shared_by_user_id AS shared_by_user_id,
                    shared_by.login_id AS shared_by_login_id,
                    shared_by.display_name AS shared_by_display_name,
                    report_shares.shared_with_user_id AS shared_with_user_id,
                    shared_with.login_id AS shared_with_login_id,
                    shared_with.display_name AS shared_with_display_name,
                    report_shares.permission AS permission,
                    report_shares.note AS note,
                    report_shares.created_at AS created_at
                FROM report_shares
                INNER JOIN users AS shared_by ON shared_by.id = report_shares.shared_by_user_id
                INNER JOIN users AS shared_with ON shared_with.id = report_shares.shared_with_user_id
                WHERE report_shares.report_id = %s
                ORDER BY report_shares.created_at DESC
                """,
                (report_id,),
            ).fetchall()
        return [self._to_view(row) for row in rows]

    def list_received_by_user(
        self,
        *,
        shared_with_user_id: str,
        limit: int = 50,
    ) -> list[ReceivedReportShareView]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT
                    report_shares.id AS share_id,
                    report_shares.report_id AS report_id,
                    reports.session_id AS session_id,
                    reports.report_type AS report_type,
                    reports.version AS version,
                    reports.file_artifact_id AS file_artifact_id,
                    reports.file_path AS file_path,
                    reports.insight_source AS insight_source,
                    reports.generated_by_user_id AS generated_by_user_id,
                    reports.generated_at AS generated_at,
                    report_shares.shared_by_user_id AS shared_by_user_id,
                    shared_by.login_id AS shared_by_login_id,
                    shared_by.display_name AS shared_by_display_name,
                    report_shares.permission AS permission,
                    report_shares.note AS note,
                    report_shares.created_at AS shared_at
                FROM report_shares
                INNER JOIN reports ON reports.id = report_shares.report_id
                INNER JOIN users AS shared_by ON shared_by.id = report_shares.shared_by_user_id
                WHERE report_shares.shared_with_user_id = %s
                ORDER BY report_shares.created_at DESC
                LIMIT %s
                """,
                (shared_with_user_id, limit),
            ).fetchall()
        return [self._to_received_view(row) for row in rows]

    def _get_view_by_id(self, share_id: str) -> ReportShareView:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT
                    report_shares.id AS share_id,
                    report_shares.report_id AS report_id,
                    report_shares.shared_by_user_id AS shared_by_user_id,
                    shared_by.login_id AS shared_by_login_id,
                    shared_by.display_name AS shared_by_display_name,
                    report_shares.shared_with_user_id AS shared_with_user_id,
                    shared_with.login_id AS shared_with_login_id,
                    shared_with.display_name AS shared_with_display_name,
                    report_shares.permission AS permission,
                    report_shares.note AS note,
                    report_shares.created_at AS created_at
                FROM report_shares
                INNER JOIN users AS shared_by ON shared_by.id = report_shares.shared_by_user_id
                INNER JOIN users AS shared_with ON shared_with.id = report_shares.shared_with_user_id
                WHERE report_shares.id = %s
                """,
                (share_id,),
            ).fetchone()
        return self._to_view(row)

    @staticmethod
    def _to_view(row) -> ReportShareView:
        return ReportShareView(
            id=row["share_id"],
            report_id=row["report_id"],
            shared_by_user_id=row["shared_by_user_id"],
            shared_by_login_id=row["shared_by_login_id"],
            shared_by_display_name=row["shared_by_display_name"],
            shared_with_user_id=row["shared_with_user_id"],
            shared_with_login_id=row["shared_with_login_id"],
            shared_with_display_name=row["shared_with_display_name"],
            permission=row["permission"],
            note=row["note"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_received_view(row) -> ReceivedReportShareView:
        return ReceivedReportShareView(
            share_id=row["share_id"],
            report_id=row["report_id"],
            session_id=row["session_id"],
            report_type=row["report_type"],
            version=row["version"],
            file_artifact_id=row["file_artifact_id"],
            file_path=row["file_path"],
            insight_source=row["insight_source"],
            generated_by_user_id=row["generated_by_user_id"],
            generated_at=row["generated_at"],
            shared_by_user_id=row["shared_by_user_id"],
            shared_by_login_id=row["shared_by_login_id"],
            shared_by_display_name=row["shared_by_display_name"],
            permission=row["permission"],
            note=row["note"],
            shared_at=row["shared_at"],
        )
