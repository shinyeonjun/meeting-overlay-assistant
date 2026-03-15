"""SQLite 리포트 저장소 구현."""

from __future__ import annotations

from server.app.domain.models.report import Report
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.repositories.contracts.report_repository import ReportRepository


class SQLiteReportRepository(ReportRepository):
    """SQLite 기반 리포트 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, report: Report) -> Report:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (
                    id,
                    session_id,
                    report_type,
                    version,
                    file_path,
                    insight_source,
                    generated_by_user_id,
                    generated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.id,
                    report.session_id,
                    report.report_type,
                    report.version,
                    report.file_path,
                    report.insight_source,
                    report.generated_by_user_id,
                    report.generated_at,
                ),
            )
            connection.commit()
        return report

    def list_by_session(self, session_id: str) -> list[Report]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reports WHERE session_id = ? ORDER BY generated_at ASC",
                (session_id,),
            ).fetchall()
        return [
            Report(
                id=row["id"],
                session_id=row["session_id"],
                report_type=row["report_type"],
                version=row["version"],
                file_path=row["file_path"],
                generated_at=row["generated_at"],
                insight_source=row["insight_source"],
                generated_by_user_id=row["generated_by_user_id"],
            )
            for row in rows
        ]

    def get_by_id(self, report_id: str) -> Report | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
        if row is None:
            return None
        return Report(
            id=row["id"],
            session_id=row["session_id"],
            report_type=row["report_type"],
            version=row["version"],
            file_path=row["file_path"],
            generated_at=row["generated_at"],
            insight_source=row["insight_source"],
            generated_by_user_id=row["generated_by_user_id"],
        )

    def get_next_version(self, session_id: str, report_type: str) -> int:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(version), 0) AS max_version
                FROM reports
                WHERE session_id = ? AND report_type = ?
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
        query = """
            SELECT reports.*
            FROM reports
            JOIN sessions ON sessions.id = reports.session_id
        """
        params: list[object] = []
        conditions: list[str] = []

        if generated_by_user_id is not None:
            conditions.append("reports.generated_by_user_id = ?")
            params.append(generated_by_user_id)
        if account_id is not None:
            conditions.append("sessions.account_id = ?")
            params.append(account_id)
        if contact_id is not None:
            conditions.append("sessions.contact_id = ?")
            params.append(contact_id)
        if context_thread_id is not None:
            conditions.append("sessions.context_thread_id = ?")
            params.append(context_thread_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY reports.generated_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._database.connect() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [
            Report(
                id=row["id"],
                session_id=row["session_id"],
                report_type=row["report_type"],
                version=row["version"],
                file_path=row["file_path"],
                generated_at=row["generated_at"],
                insight_source=row["insight_source"],
                generated_by_user_id=row["generated_by_user_id"],
            )
            for row in rows
        ]
