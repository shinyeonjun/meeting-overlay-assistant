"""PostgreSQL retrieval 저장소의 JSONB 값 변환 유틸리티."""

from __future__ import annotations

import json


def dump_jsonb(value: dict[str, object] | None) -> str:
    """dict 값을 psycopg JSONB 파라미터로 넘길 문자열로 변환한다."""

    return json.dumps(value or {}, ensure_ascii=False)


def load_jsonb_object(value) -> dict[str, object]:
    """PostgreSQL JSONB 조회 결과를 dict로 정규화한다."""

    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}
