"""SQLite 리포트 저장소 구현."""

from __future__ import annotations

from backend.app.domain.models.report import Report
from backend.app.infrastructure.persistence.sqlite.database import Database
from backend.app.repositories.contracts.report_repository import ReportRepository


class SQLiteReportRepository(ReportRepository):
    """SQLite 기반 리포트 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, report: Report) -> Report:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (
                    id, session_id, report_type, version, file_path, insight_source, snapshot_markdown, generated_at
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
                    report.snapshot_markdown,
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
                snapshot_markdown=row["snapshot_markdown"],
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
            snapshot_markdown=row["snapshot_markdown"],
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
