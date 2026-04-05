"""세션 후처리 job repository SQL helper."""

from __future__ import annotations


INSERT_QUERY = """
    INSERT INTO session_post_processing_jobs (
        id,
        session_id,
        status,
        recording_artifact_id,
        recording_path,
        error_message,
        requested_by_user_id,
        claimed_by_worker_id,
        lease_expires_at,
        attempt_count,
        created_at,
        started_at,
        completed_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


UPDATE_QUERY = """
    UPDATE session_post_processing_jobs
    SET
        status = %s,
        recording_artifact_id = %s,
        recording_path = %s,
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


GET_BY_ID_QUERY = "SELECT * FROM session_post_processing_jobs WHERE id = %s"


GET_LATEST_BY_SESSION_QUERY = """
    SELECT *
    FROM session_post_processing_jobs
    WHERE session_id = %s
    ORDER BY created_at DESC, id DESC
    LIMIT 1
"""


LIST_PENDING_QUERY = """
    SELECT *
    FROM session_post_processing_jobs
    WHERE status = %s
    ORDER BY created_at ASC, id ASC
    LIMIT %s
"""


CLAIM_AVAILABLE_QUERY = """
    SELECT *
    FROM session_post_processing_jobs
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
