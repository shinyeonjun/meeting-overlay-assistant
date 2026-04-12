"""PostgreSQL 데이터베이스 연결 래퍼."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


class PostgreSQLDatabase:
    """psycopg 연결과 트랜잭션 범위를 감싸는 얇은 래퍼."""

    def __init__(
        self,
        dsn: str,
        *,
        connect_timeout: int = 5,
        application_name: str = "caps-server",
    ) -> None:
        self._dsn = dsn
        self._connect_timeout = connect_timeout
        self._application_name = application_name

    def connect(self):
        """dict row 기반 PostgreSQL 연결을 연다."""

        psycopg, dict_row = self._load_driver()
        return psycopg.connect(
            self._dsn,
            connect_timeout=self._connect_timeout,
            application_name=self._application_name,
            row_factory=dict_row,
        )

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """자동 commit/rollback 트랜잭션 범위를 연다."""

        with self.connect() as connection:
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

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
