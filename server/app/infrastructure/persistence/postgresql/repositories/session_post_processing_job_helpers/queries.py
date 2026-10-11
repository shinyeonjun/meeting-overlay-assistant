"""세션 후처리 job repository SQL helper."""

from __future__ import annotations

from server.app.infrastructure.persistence.postgresql.repositories.job_sql_templates import (
    build_claim_available_query,
    build_renew_lease_query,
    build_list_pending_query,
    build_get_latest_by_session_query,
    build_get_by_id_query,
)


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


# worker fencing: 만료된 lease로 다른 worker에게 넘어간 뒤의 늦은 쓰기를 거부한다.
FENCED_UPDATE_QUERY = UPDATE_QUERY.rstrip() + """
  AND status = 'processing'
  AND claimed_by_worker_id = %s
"""


GET_BY_ID_QUERY = build_get_by_id_query("session_post_processing_jobs")


GET_LATEST_BY_SESSION_QUERY = build_get_latest_by_session_query("session_post_processing_jobs")


LIST_PENDING_QUERY = build_list_pending_query("session_post_processing_jobs")


CLAIM_AVAILABLE_QUERY = build_claim_available_query("session_post_processing_jobs")


RENEW_LEASE_QUERY = build_renew_lease_query("session_post_processing_jobs")


# lease가 만료된 채 최대 시도 횟수에 도달한 job은 더 claim하지 않고 실패로 확정한다.
# 그대로 두면 worker를 죽이는 poison job이 lease 만료마다 무한히 재시도된다.
EXHAUST_STALE_QUERY = """
    UPDATE session_post_processing_jobs
    SET
        status = 'failed',
        error_message = 'lease 만료가 최대 시도 횟수만큼 반복되어 중단했습니다.',
        claimed_by_worker_id = NULL,
        lease_expires_at = NULL,
        completed_at = %s
    WHERE status = 'processing'
      AND (lease_expires_at IS NULL OR lease_expires_at <= %s)
      AND attempt_count >= %s
"""
