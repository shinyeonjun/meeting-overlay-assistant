"""PostgreSQL 리포트 생성 job 저장소 구현."""

from __future__ import annotations

from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories.report_generation_job_helpers import (
    CLAIM_AVAILABLE_QUERY,
    GET_BY_ID_QUERY,
    GET_LATEST_BY_SESSION_QUERY,
    GET_LATEST_BY_SESSIONS_QUERY,
    INSERT_QUERY,
    LIST_PENDING_QUERY,
    UPDATE_QUERY,
    job_to_insert_row,
    job_to_update_row,
    row_to_job,
)
from server.app.repositories.contracts.report_generation_job_repository import (
    ReportGenerationJobRepository,
)


class PostgreSQLReportGenerationJobRepository(ReportGenerationJobRepository):
    """PostgreSQL 기반 리포트 생성 job 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def save(self, job: ReportGenerationJob) -> ReportGenerationJob:
        with self._database.transaction() as connection:
            connection.execute(INSERT_QUERY, job_to_insert_row(job))
        return job

    def update(self, job: ReportGenerationJob) -> ReportGenerationJob:
        with self._database.transaction() as connection:
            connection.execute(UPDATE_QUERY, job_to_update_row(job))
        return job

    def get_by_id(self, job_id: str) -> ReportGenerationJob | None:
        with self._database.transaction() as connection:
            row = connection.execute(GET_BY_ID_QUERY, (job_id,)).fetchone()
        return row_to_job(row)

    def get_latest_by_session(self, session_id: str) -> ReportGenerationJob | None:
        with self._database.transaction() as connection:
            row = connection.execute(GET_LATEST_BY_SESSION_QUERY, (session_id,)).fetchone()
        return row_to_job(row)

    def get_latest_by_sessions(self, session_ids: list[str]) -> dict[str, ReportGenerationJob]:
        if not session_ids:
            return {}

        normalized_ids = list(dict.fromkeys(session_ids))
        with self._database.transaction() as connection:
            rows = connection.execute(GET_LATEST_BY_SESSIONS_QUERY, (normalized_ids,)).fetchall()
        return {
            job.session_id: job
            for row in rows
            if (job := row_to_job(row)) is not None
        }

    def list_pending(self, limit: int = 10) -> list[ReportGenerationJob]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                LIST_PENDING_QUERY,
                ("pending", max(limit, 1)),
            ).fetchall()
        return [job for row in rows if (job := row_to_job(row)) is not None]

    def claim_available(
        self,
        *,
        worker_id: str,
        lease_expires_at: str,
        claimed_at: str,
        limit: int = 10,
    ) -> list[ReportGenerationJob]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                CLAIM_AVAILABLE_QUERY,
                ("pending", "processing", claimed_at, "pending", max(limit, 1)),
            ).fetchall()

            claimed_jobs: list[ReportGenerationJob] = []
            for row in rows:
                job = row_to_job(row)
                if job is None:
                    continue
                claimed_job = job.mark_processing(
                    claimed_by_worker_id=worker_id,
                    lease_expires_at=lease_expires_at,
                    started_at=claimed_at,
                )
                connection.execute(UPDATE_QUERY, job_to_update_row(claimed_job))
                claimed_jobs.append(claimed_job)
        return claimed_jobs
