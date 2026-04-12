"""SQLite 리포트 생성 job 저장소 구현."""

from __future__ import annotations

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.infrastructure.persistence.sqlite.database import Database
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)


class SQLiteReportGenerationJobRepository(ReportGenerationJobRepository):
    """SQLite 기반 리포트 생성 job 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, job: ReportGenerationJob) -> ReportGenerationJob:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO report_generation_jobs (
                    id,
                    session_id,
                    status,
                    recording_path,
                    transcript_path,
                    markdown_report_id,
                    pdf_report_id,
                    error_message,
                    requested_by_user_id,
                    created_at,
                    started_at,
                    completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.session_id,
                    job.status,
                    job.recording_path,
                    job.transcript_path,
                    job.markdown_report_id,
                    job.pdf_report_id,
                    job.error_message,
                    job.requested_by_user_id,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                ),
            )
            connection.commit()
        return job

    def update(self, job: ReportGenerationJob) -> ReportGenerationJob:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE report_generation_jobs
                SET
                    status = ?,
                    recording_path = ?,
                    transcript_path = ?,
                    markdown_report_id = ?,
                    pdf_report_id = ?,
                    error_message = ?,
                    requested_by_user_id = ?,
                    created_at = ?,
                    started_at = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    job.status,
                    job.recording_path,
                    job.transcript_path,
                    job.markdown_report_id,
                    job.pdf_report_id,
                    job.error_message,
                    job.requested_by_user_id,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
                    job.id,
                ),
            )
            connection.commit()
        return job

    def get_by_id(self, job_id: str) -> ReportGenerationJob | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM report_generation_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        return self._to_model(row)

    def get_latest_by_session(self, session_id: str) -> ReportGenerationJob | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM report_generation_jobs
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        return self._to_model(row)

    @staticmethod
    def _to_model(row) -> ReportGenerationJob | None:
        if row is None:
            return None
        return ReportGenerationJob(
            id=row["id"],
            session_id=row["session_id"],
            status=row["status"],
            recording_path=row["recording_path"],
            transcript_path=row["transcript_path"],
            markdown_report_id=row["markdown_report_id"],
            pdf_report_id=row["pdf_report_id"],
            error_message=row["error_message"],
            requested_by_user_id=row["requested_by_user_id"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )
