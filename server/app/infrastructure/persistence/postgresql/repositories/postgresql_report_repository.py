"""PostgreSQL 리포트 저장소 구현."""

from __future__ import annotations

from server.app.domain.models.report import Report
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.repositories.contracts.report_repository import ReportRepository
from server.app.services.reports.report_models import SessionReportSummary


class PostgreSQLReportRepository(ReportRepository):
    """PostgreSQL 기반 리포트 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def save(self, report: Report) -> Report:
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO reports (
                    id,
                    session_id,
                    report_type,
                    version,
                    file_artifact_id,
                    file_path,
                    insight_source,
                    generated_by_user_id,
                    generated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    report.id,
                    report.session_id,
                    report.report_type,
                    report.version,
                    report.file_artifact_id,
                    report.file_path,
                    report.insight_source,
                    report.generated_by_user_id,
                    report.generated_at,
                ),
            )
        return report

    def list_by_session(self, session_id: str) -> list[Report]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM reports WHERE session_id = %s ORDER BY generated_at ASC",
                (session_id,),
            ).fetchall()
        return [self._to_report(row) for row in rows]

    def get_by_id(self, report_id: str) -> Report | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE id = %s",
                (report_id,),
            ).fetchone()
        return self._to_report(row) if row is not None else None

    def get_next_version(self, session_id: str, report_type: str) -> int:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) AS max_version
                FROM reports
                WHERE session_id = %s AND report_type = %s
                """,
                (session_id, report_type),
            ).fetchone()
        return int(row["max_version"]) + 1

    def list_recent(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int | None = 50,
    ) -> list[Report]:
        query, params = self._build_recent_query(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            select_clause="SELECT reports.*",
            limit=limit,
            order_by_generated_at=True,
        )
        with self._database.transaction() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._to_report(row) for row in rows]

    def count_recent(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        query, params = self._build_recent_query(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            select_clause="SELECT COUNT(*) AS total",
            limit=None,
            order_by_generated_at=False,
        )
        with self._database.transaction() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
        return int(row["total"]) if row is not None else 0

    def get_session_summaries(self, session_ids: list[str]) -> dict[str, SessionReportSummary]:
        if not session_ids:
            return {}

        normalized_ids = list(dict.fromkeys(session_ids))
        summaries = {
            session_id: SessionReportSummary(session_id=session_id, report_count=0)
            for session_id in normalized_ids
        }

        with self._database.transaction() as connection:
            count_rows = connection.execute(
                """
                SELECT session_id, COUNT(*) AS report_count
                FROM reports
                WHERE session_id = ANY(%s)
                GROUP BY session_id
                """,
                (normalized_ids,),
            ).fetchall()
            latest_rows = connection.execute(
                """
                SELECT DISTINCT ON (session_id) *
                FROM reports
                WHERE session_id = ANY(%s)
                ORDER BY session_id, generated_at DESC, id DESC
                """,
                (normalized_ids,),
            ).fetchall()

        for row in count_rows:
            session_id = row["session_id"]
            summaries[session_id] = SessionReportSummary(
                session_id=session_id,
                report_count=int(row["report_count"]),
                latest_report=summaries[session_id].latest_report,
            )

        for row in latest_rows:
            latest_report = self._to_report(row)
            summaries[latest_report.session_id] = SessionReportSummary(
                session_id=latest_report.session_id,
                report_count=summaries[latest_report.session_id].report_count,
                latest_report=latest_report,
            )

        return summaries

    def _build_recent_query(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        select_clause: str,
        limit: int | None,
        order_by_generated_at: bool,
    ) -> tuple[str, list[object]]:
        query = f"""
            {select_clause}
            FROM reports
            JOIN sessions ON sessions.id = reports.session_id
        """
        params: list[object] = []
        conditions: list[str] = []

        if generated_by_user_id is not None:
            conditions.append("reports.generated_by_user_id = %s")
            params.append(generated_by_user_id)
        if account_id is not None:
            conditions.append("sessions.account_id = %s")
            params.append(account_id)
        if contact_id is not None:
            conditions.append("sessions.contact_id = %s")
            params.append(contact_id)
        if context_thread_id is not None:
            conditions.append("sessions.context_thread_id = %s")
            params.append(context_thread_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        if order_by_generated_at:
            query += " ORDER BY reports.generated_at DESC"
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        return query, params

    @staticmethod
    def _to_report(row) -> Report:
        return Report(
            id=row["id"],
            session_id=row["session_id"],
            report_type=row["report_type"],
            version=row["version"],
            file_artifact_id=row["file_artifact_id"],
            file_path=row["file_path"],
            generated_at=row["generated_at"],
            insight_source=row["insight_source"],
            generated_by_user_id=row["generated_by_user_id"],
        )
