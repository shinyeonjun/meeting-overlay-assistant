"""SQLite 연결과 초기화 진입점."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from server.app.core.config import settings
from server.app.infrastructure.persistence.sqlite.migrations import (
    run_sqlite_migrations,
)
from server.app.infrastructure.persistence.sqlite.schema import SCHEMA_SQL


class Database:
    """SQLite 데이터베이스 연결 객체."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @property
    def database_path(self) -> Path:
        """데이터베이스 파일 경로를 반환한다."""

        return self._database_path

    def initialize(self) -> None:
        """기본 스키마와 마이그레이션을 적용한다."""

        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            run_sqlite_migrations(connection)
            connection.commit()

    def connect(self) -> sqlite3.Connection:
        """SQLite 연결을 만든다."""

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self):
        """하나의 트랜잭션 범위를 제공한다."""

        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


database = Database(settings.database_path)
