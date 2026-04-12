"""PostgreSQL 저장소 공통 유틸."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase


def parse_json_value(value: Any, *, default: Any) -> Any:
    """문자열/파이썬 객체 형태 JSON 값을 공통 형태로 바꾼다."""

    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return default
    return value


def parse_string_array(value: Any) -> list[str]:
    """JSON 배열 또는 파이썬 리스트를 문자열 배열로 정규화한다."""

    parsed = parse_json_value(value, default=[])
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def to_jsonb_parameter(value: Any) -> Any:
    """psycopg가 JSONB로 안전하게 저장할 수 있는 파라미터로 감싼다."""

    try:
        from psycopg.types.json import Jsonb
    except ImportError as exc:  # pragma: no cover - PostgreSQL 런타임 전용
        raise RuntimeError(
            "PostgreSQL JSONB 저장을 사용하려면 psycopg 패키지가 필요합니다.",
        ) from exc
    return Jsonb(value)


def epoch_ms_to_timestamptz(value: int | None) -> datetime | None:
    """epoch milliseconds 값을 UTC datetime으로 변환한다."""

    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def timestamptz_to_epoch_ms(value: Any) -> int:
    """PostgreSQL TIMESTAMPTZ 값을 epoch milliseconds로 변환한다."""

    if value is None:
        return 0
    if isinstance(value, datetime):
        target = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return int(target.timestamp() * 1000)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return 0
        target = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        return int(target.timestamp() * 1000)
    return int(value)


class PostgreSQLRepositoryBase:
    """PostgreSQL 저장소 공통 베이스 클래스."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    @contextmanager
    def _connection_scope(self, connection: Any | None) -> Iterator[Any]:
        if connection is not None:
            yield connection
            return
        with self._database.transaction() as managed_connection:
            yield managed_connection
