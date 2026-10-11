"""Note correction job repository SQL helper."""

from __future__ import annotations

from server.app.infrastructure.persistence.postgresql.repositories.job_sql_templates import (
    build_claim_available_query,
    build_renew_lease_query,
    build_list_pending_query,
    build_get_latest_by_session_query,
    build_get_by_id_query,
)


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


GET_BY_ID_QUERY = build_get_by_id_query("note_correction_jobs")


GET_LATEST_BY_SESSION_QUERY = build_get_latest_by_session_query("note_correction_jobs")


GET_LATEST_BY_SESSIONS_QUERY = """
    SELECT DISTINCT ON (session_id) *
    FROM note_correction_jobs
    WHERE session_id = ANY(%s)
    ORDER BY session_id, created_at DESC, id DESC
"""


LIST_PENDING_QUERY = build_list_pending_query("note_correction_jobs")


CLAIM_AVAILABLE_QUERY = build_claim_available_query("note_correction_jobs")


RENEW_LEASE_QUERY = build_renew_lease_query("note_correction_jobs")


# lease가 만료된 채 최대 시도 횟수에 도달한 job은 더 claim하지 않고 실패로 확정한다.
# 그대로 두면 worker를 죽이는 poison job이 lease 만료마다 무한히 재시도된다.
EXHAUST_STALE_QUERY = """
    UPDATE note_correction_jobs
    SET
        status = 'failed',
        error_message = 'lease 만료가 최대 시도 횟수만큼 반복되어 중단했습니다.',
        claimed_by_worker_id = NULL,
        lease_expires_at = NULL,
        completed_at = %s
    WHERE status = 'processing'
      AND (lease_expires_at IS NULL OR lease_expires_at <= %s)
      AND attempt_count >= %s
    RETURNING id
"""


# worker fencing: claim을 잃은 worker의 늦은 쓰기를 거부한다.
FENCED_UPDATE_QUERY = UPDATE_QUERY.rstrip() + """
  AND status = 'processing'
  AND claimed_by_worker_id = %s
"""
