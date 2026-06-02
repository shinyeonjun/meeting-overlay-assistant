"""PostgreSQL assistant response job repository."""

from __future__ import annotations

from server.app.domain.models.assistant_response_job import AssistantResponseJob
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories._base import parse_json_value
from server.app.infrastructure.persistence.postgresql.repositories.retrieval.jsonb import (
    dump_jsonb,
)
from server.app.repositories.contracts.assistant_response_job_repository import (
    AssistantResponseJobRepository,
)


INSERT_QUERY = """
    INSERT INTO assistant_response_jobs (
        id,
        conversation_id,
        user_message_id,
        assistant_message_id,
        workspace_id,
        status,
        query,
        request_json,
        error_message,
        requested_by_user_id,
        claimed_by_worker_id,
        lease_expires_at,
        attempt_count,
        created_at,
        started_at,
        completed_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s)
"""

UPDATE_QUERY = """
    UPDATE assistant_response_jobs
    SET
        status = %s,
        query = %s,
        request_json = %s::jsonb,
        error_message = %s,
        requested_by_user_id = %s,
        claimed_by_worker_id = %s,
        lease_expires_at = %s,
        attempt_count = %s,
        created_at = %s,
        started_at = %s,
        completed_at = %s
    WHERE id = %s
"""

GET_BY_ID_QUERY = "SELECT * FROM assistant_response_jobs WHERE id = %s"

LIST_PENDING_QUERY = """
    SELECT *
    FROM assistant_response_jobs
    WHERE status = %s
    ORDER BY created_at ASC, id ASC
    LIMIT %s
"""

CLAIM_AVAILABLE_QUERY = """
    SELECT *
    FROM assistant_response_jobs
    WHERE status = %s
       OR (
            status = %s
            AND (lease_expires_at IS NULL OR lease_expires_at <= %s)
       )
    ORDER BY
        CASE WHEN status = %s THEN 0 ELSE 1 END,
        created_at ASC,
        id ASC
    FOR UPDATE SKIP LOCKED
    LIMIT %s
"""

RENEW_LEASE_QUERY = """
    UPDATE assistant_response_jobs
    SET lease_expires_at = %s
    WHERE id = %s
      AND status = %s
      AND claimed_by_worker_id = %s
"""


class PostgreSQLAssistantResponseJobRepository(AssistantResponseJobRepository):
    """PostgreSQL backed assistant response job repository."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def save(self, job: AssistantResponseJob) -> AssistantResponseJob:
        with self._database.transaction() as connection:
            connection.execute(INSERT_QUERY, _job_to_insert_row(job))
        return job

    def update(self, job: AssistantResponseJob) -> AssistantResponseJob:
        with self._database.transaction() as connection:
            connection.execute(UPDATE_QUERY, _job_to_update_row(job))
        return job

    def get_by_id(self, job_id: str) -> AssistantResponseJob | None:
        with self._database.transaction() as connection:
            row = connection.execute(GET_BY_ID_QUERY, (job_id,)).fetchone()
        return _row_to_job(row)

    def list_pending(self, limit: int = 10) -> list[AssistantResponseJob]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                LIST_PENDING_QUERY,
                ("pending", max(limit, 1)),
            ).fetchall()
        return [job for row in rows if (job := _row_to_job(row)) is not None]

    def claim_available(
        self,
        *,
        worker_id: str,
        lease_expires_at: str,
        claimed_at: str,
        limit: int = 10,
    ) -> list[AssistantResponseJob]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                CLAIM_AVAILABLE_QUERY,
                ("pending", "processing", claimed_at, "pending", max(limit, 1)),
            ).fetchall()

            claimed_jobs: list[AssistantResponseJob] = []
            for row in rows:
                job = _row_to_job(row)
                if job is None:
                    continue
                claimed_job = job.mark_processing(
                    claimed_by_worker_id=worker_id,
                    lease_expires_at=lease_expires_at,
                    started_at=claimed_at,
                )
                connection.execute(UPDATE_QUERY, _job_to_update_row(claimed_job))
                claimed_jobs.append(claimed_job)
        return claimed_jobs

    def renew_lease(
        self,
        *,
        job_id: str,
        worker_id: str,
        lease_expires_at: str,
    ) -> bool:
        with self._database.transaction() as connection:
            result = connection.execute(
                RENEW_LEASE_QUERY,
                (lease_expires_at, job_id, "processing", worker_id),
            )
        return result.rowcount > 0


def _job_to_insert_row(job: AssistantResponseJob) -> tuple[object, ...]:
    return (
        job.id,
        job.conversation_id,
        job.user_message_id,
        job.assistant_message_id,
        job.workspace_id,
        job.status,
        job.query,
        dump_jsonb(job.request_json),
        job.error_message,
        job.requested_by_user_id,
        job.claimed_by_worker_id,
        job.lease_expires_at,
        job.attempt_count,
        job.created_at,
        job.started_at,
        job.completed_at,
    )


def _job_to_update_row(job: AssistantResponseJob) -> tuple[object, ...]:
    return (
        job.status,
        job.query,
        dump_jsonb(job.request_json),
        job.error_message,
        job.requested_by_user_id,
        job.claimed_by_worker_id,
        job.lease_expires_at,
        job.attempt_count,
        job.created_at,
        job.started_at,
        job.completed_at,
        job.id,
    )


def _row_to_job(row) -> AssistantResponseJob | None:
    if row is None:
        return None
    request_json = parse_json_value(row["request_json"], default={})
    return AssistantResponseJob(
        id=row["id"],
        conversation_id=row["conversation_id"],
        user_message_id=row["user_message_id"],
        assistant_message_id=row["assistant_message_id"],
        workspace_id=row["workspace_id"],
        status=row["status"],
        query=row["query"],
        request_json=request_json if isinstance(request_json, dict) else {},
        error_message=row["error_message"],
        requested_by_user_id=row["requested_by_user_id"],
        claimed_by_worker_id=row["claimed_by_worker_id"],
        lease_expires_at=row["lease_expires_at"],
        attempt_count=int(row["attempt_count"] or 0),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )
