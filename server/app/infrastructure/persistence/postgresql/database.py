"""PostgreSQL 데이터베이스 연결 풀과 트랜잭션 범위."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

# 시각 컬럼은 TIMESTAMPTZ로 저장하고, 애플리케이션에는 UTC ISO 문자열로 돌려준다.
# 도메인 객체가 시각을 문자열로 다루기 때문에 로더 한 곳에서 변환한다.
_TIMESTAMPTZ_OID = 1184
_DEFAULT_POOL_MIN_SIZE = 1
_DEFAULT_POOL_MAX_SIZE = 10


def _build_timestamptz_loader():
    from psycopg.adapt import Loader
    from psycopg.pq import Format

    class _UtcIsoTimestamptzLoader(Loader):
        format = Format.TEXT

        def load(self, data):
            text = bytes(data).decode("utf-8")
            parsed = datetime.fromisoformat(text)
            return parsed.astimezone(timezone.utc).isoformat()

    return _UtcIsoTimestamptzLoader


class PostgreSQLDatabase:
    """psycopg 연결 풀과 트랜잭션 범위를 감싸는 래퍼."""

    def __init__(
        self,
        dsn: str,
        *,
        connect_timeout: int = 5,
        application_name: str = "caps-server",
        pool_min_size: int = _DEFAULT_POOL_MIN_SIZE,
        pool_max_size: int = _DEFAULT_POOL_MAX_SIZE,
    ) -> None:
        self._dsn = dsn
        self._connect_timeout = connect_timeout
        self._application_name = application_name
        self._pool_min_size = pool_min_size
        self._pool_max_size = pool_max_size
        self._pool = None
        self._pool_lock = threading.Lock()

    def _get_pool(self):
        if self._pool is not None:
            return self._pool
        with self._pool_lock:
            if self._pool is None:
                self._pool = self._create_pool()
        return self._pool

    def _create_pool(self):
        _, dict_row = self._load_driver()
        from psycopg_pool import ConnectionPool

        loader_class = _build_timestamptz_loader()

        def configure(connection) -> None:
            connection.adapters.register_loader(_TIMESTAMPTZ_OID, loader_class)

        return ConnectionPool(
            conninfo=self._dsn,
            min_size=self._pool_min_size,
            max_size=self._pool_max_size,
            kwargs={
                "connect_timeout": self._connect_timeout,
                "application_name": self._application_name,
                "row_factory": dict_row,
            },
            configure=configure,
            open=True,
        )

    def connect(self):
        """풀에서 연결 하나를 빌린다. 블록을 나가면 commit 후 풀에 돌려준다."""

        return self._get_pool().connection()

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """자동 commit/rollback 트랜잭션 범위를 연다."""

        with self.connect() as connection:
            yield connection

    def close(self) -> None:
        """풀의 모든 연결을 닫는다. DB를 삭제하기 전에 호출해야 한다."""

        with self._pool_lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.close()

    @staticmethod
    def _load_driver():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL 저장소를 사용하려면 psycopg 패키지가 필요합니다.",
            ) from exc
        return psycopg, dict_row
