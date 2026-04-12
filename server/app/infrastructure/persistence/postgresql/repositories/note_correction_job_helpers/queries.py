"""Note correction job repository SQL helper."""

from __future__ import annotations


INSERT_QUERY = """
    INSERT INTO note_correction_jobs (
        id,
        session_id,
        source_version,
        status,
        error_message,
        requested_by_user_id,
        claimed_by_worker_id,
        lease_expires_at,
        attempt_count,
        created_at,
        started_at,
        completed_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


UPDATE_QUERY = """
    UPDATE note_correction_jobs
    SET
        source_version = %s,
        status = %s,
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


GET_BY_ID_QUERY = "SELECT * FROM note_correction_jobs WHERE id = %s"


GET_LATEST_BY_SESSION_QUERY = """
    SELECT *
    FROM note_correction_jobs
    WHERE session_id = %s
    ORDER BY created_at DESC, id DESC
    LIMIT 1
"""


GET_LATEST_BY_SESSIONS_QUERY = """
    SELECT DISTINCT ON (session_id) *
    FROM note_correction_jobs
    WHERE session_id = ANY(%s)
    ORDER BY session_id, created_at DESC, id DESC
"""


LIST_PENDING_QUERY = """
    SELECT *
    FROM note_correction_jobs
    WHERE status = %s
    ORDER BY created_at ASC, id ASC
    LIMIT %s
"""


CLAIM_AVAILABLE_QUERY = """
    SELECT *
    FROM note_correction_jobs
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
    UPDATE note_correction_jobs
    SET lease_expires_at = %s
    WHERE id = %s
      AND status = %s
      AND claimed_by_worker_id = %s
"""
