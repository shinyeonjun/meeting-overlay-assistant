"""SQLite 마이그레이션 공통 도우미."""

from __future__ import annotations

import sqlite3


def get_table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """테이블 컬럼 이름 집합을 반환한다."""

    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
