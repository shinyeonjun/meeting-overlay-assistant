"""세 종류 job(세션 후처리, 노트 보정, 리포트 생성)이 공유하는 SQL 템플릿.

테이블 이름만 다르므로 한 곳에서 만든다.
"""

from __future__ import annotations


def build_claim_available_query(table: str) -> str:
    return '\n    SELECT *\n    FROM <T>\n    WHERE status = %s\n       OR (\n            status = %s\n            AND (lease_expires_at IS NULL OR lease_expires_at <= %s)\n            AND attempt_count < %s\n       )\n    ORDER BY\n        CASE WHEN status = %s THEN 0 ELSE 1 END,\n        created_at ASC,\n        id ASC\n    FOR UPDATE SKIP LOCKED\n    LIMIT %s\n'.replace("<T>", table)


def build_renew_lease_query(table: str) -> str:
    return '\n    UPDATE <T>\n    SET lease_expires_at = %s\n    WHERE id = %s\n      AND status = %s\n      AND claimed_by_worker_id = %s\n'.replace("<T>", table)


def build_list_pending_query(table: str) -> str:
    return '\n    SELECT *\n    FROM <T>\n    WHERE status = %s\n    ORDER BY created_at ASC, id ASC\n    LIMIT %s\n'.replace("<T>", table)


def build_get_latest_by_session_query(table: str) -> str:
    return '\n    SELECT *\n    FROM <T>\n    WHERE session_id = %s\n    ORDER BY created_at DESC, id DESC\n    LIMIT 1\n'.replace("<T>", table)


def build_get_by_id_query(table: str) -> str:
    return 'SELECT * FROM <T> WHERE id = %s'.replace("<T>", table)
