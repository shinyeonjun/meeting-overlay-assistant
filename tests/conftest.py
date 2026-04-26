"""테스트 공통 fixture."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = Path(__file__).resolve().parent
FIXTURES_ROOT = TESTS_ROOT / "fixtures"
SUPPORT_FIXTURES_ROOT = FIXTURES_ROOT / "support"
VIDEO_FIXTURES_ROOT = FIXTURES_ROOT / "video"
POSTGRESQL_SCHEMA_PATHS = (
    PROJECT_ROOT
    / "server"
    / "app"
    / "infrastructure"
    / "persistence"
    / "postgresql"
    / "000_runtime_compatible_schema.sql",
    PROJECT_ROOT
    / "server"
    / "app"
    / "infrastructure"
    / "persistence"
    / "postgresql"
    / "010_pgvector_knowledge.sql",
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.api.http import dependencies as dependency_module
from server.app.api.http.wiring import persistence as persistence_module
from server.app.core.config import settings
from server.app.core.workspace_defaults import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    DEFAULT_WORKSPACE_STATUS,
)
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.main import app


def _load_psycopg():
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - 테스트 환경 오류
        raise RuntimeError("PostgreSQL 테스트를 실행하려면 psycopg 패키지가 필요합니다.") from exc
    return psycopg


def _replace_database_name(dsn: str, database_name: str) -> str:
    parsed = urlsplit(dsn)
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            f"/{database_name}",
            parsed.query,
            parsed.fragment,
        )
    )


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    current_lines: list[str] = []
    in_dollar_block = False
    for line in sql_text.splitlines():
        current_lines.append(line)
        if "$$" in line:
            in_dollar_block = not in_dollar_block
        if not in_dollar_block and line.strip().endswith(";"):
            statement = "\n".join(current_lines).strip()
            if statement:
                statements.append(statement)
            current_lines = []
    tail = "\n".join(current_lines).strip()
    if tail:
        statements.append(tail)
    return statements


def _get_test_postgresql_dsn() -> str:
    explicit = os.getenv("TEST_POSTGRESQL_DSN")
    if explicit:
        return explicit

    base_dsn = settings.postgresql_dsn
    if not base_dsn:
        raise RuntimeError("테스트를 실행하려면 POSTGRESQL_DSN 또는 TEST_POSTGRESQL_DSN이 필요합니다.")
    database_name = os.getenv("TEST_POSTGRESQL_DB_NAME") or f"caps_test_{os.getpid()}"
    return _replace_database_name(base_dsn, database_name)


def _ensure_test_database_exists(test_dsn: str) -> None:
    psycopg = _load_psycopg()
    parsed = urlsplit(test_dsn)
    database_name = parsed.path.lstrip("/")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise RuntimeError(f"지원하지 않는 테스트 DB 이름입니다: {database_name}")

    admin_database_name = os.getenv("TEST_POSTGRESQL_ADMIN_DB", "postgres")
    admin_dsn = _replace_database_name(test_dsn, admin_database_name)
    with psycopg.connect(
        admin_dsn,
        autocommit=True,
        connect_timeout=5,
        application_name="caps-tests-admin",
    ) as connection:
        connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s
              AND pid <> pg_backend_pid()
            """,
            (database_name,),
        )
        connection.execute(
            f'DROP DATABASE IF EXISTS "{database_name}"',
        )
        connection.execute(
            """
            SELECT 1 AS present
            FROM pg_database
            WHERE datname = %s
            """,
            (database_name,),
        )
        connection.execute(f'CREATE DATABASE "{database_name}"')


def _apply_test_schema(database: PostgreSQLDatabase) -> None:
    with database.transaction() as connection:
        for schema_path in POSTGRESQL_SCHEMA_PATHS:
            sql_text = schema_path.read_text(encoding="utf-8-sig")
            normalized = sql_text.replace(
                "to_tsvector('simple', CONCAT_WS(' ', COALESCE(title, ''), COALESCE(body, '')))",
                "to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(body, ''))",
            )
            normalized = re.sub(
                r"(^--[^\r\n]*?)\s*(CREATE TABLE IF NOT EXISTS)",
                r"\1\n\2",
                normalized,
                flags=re.MULTILINE,
            )
            statements = _split_sql_statements(normalized)
            for statement in statements:
                if statement.startswith("--") and "\n" not in statement:
                    continue
                connection.execute(statement)


def _truncate_public_tables(database: PostgreSQLDatabase) -> None:
    with database.transaction() as connection:
        rows = connection.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename ASC
            """
        ).fetchall()
        table_names = [row["tablename"] for row in rows]
        if not table_names:
            return
        joined = ", ".join(f'"{table_name}"' for table_name in table_names)
        connection.execute(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE")


def _seed_default_workspace(database: PostgreSQLDatabase) -> None:
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO workspaces (id, slug, name, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP::text, CURRENT_TIMESTAMP::text)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                DEFAULT_WORKSPACE_ID,
                DEFAULT_WORKSPACE_SLUG,
                DEFAULT_WORKSPACE_NAME,
                DEFAULT_WORKSPACE_STATUS,
            ),
        )


@pytest.fixture(scope="session")
def postgresql_test_dsn() -> str:
    """테스트 전용 PostgreSQL DSN을 반환한다."""

    return _get_test_postgresql_dsn()


@pytest.fixture(scope="session")
def prepared_test_database(postgresql_test_dsn: str) -> PostgreSQLDatabase:
    """테스트용 PostgreSQL 데이터베이스를 준비한다."""

    _ensure_test_database_exists(postgresql_test_dsn)
    database = PostgreSQLDatabase(
        postgresql_test_dsn,
        application_name="caps-tests",
    )
    _apply_test_schema(database)
    return database


@pytest.fixture
def isolated_database(prepared_test_database: PostgreSQLDatabase, postgresql_test_dsn: str):
    """테스트마다 비워진 PostgreSQL 인스턴스를 제공한다."""

    original_topic_summarizer_backend = settings.topic_summarizer_backend
    original_analyzer_backend = settings.analyzer_backend
    original_stt_preload_on_startup = settings.stt_preload_on_startup
    original_persistence_backend = settings.persistence_backend
    original_postgresql_dsn = settings.postgresql_dsn
    original_redis_url = settings.redis_url

    _truncate_public_tables(prepared_test_database)
    _seed_default_workspace(prepared_test_database)
    object.__setattr__(settings, "topic_summarizer_backend", "noop")
    object.__setattr__(settings, "analyzer_backend", "rule_based")
    object.__setattr__(settings, "stt_preload_on_startup", False)
    object.__setattr__(settings, "persistence_backend", "postgresql")
    object.__setattr__(settings, "postgresql_dsn", postgresql_test_dsn)
    object.__setattr__(settings, "redis_url", None)
    persistence_module.get_postgresql_database.cache_clear()
    persistence_module.get_gpu_heavy_execution_gate.cache_clear()
    dependency_module._get_shared_analyzer.cache_clear()
    dependency_module._get_shared_topic_summarizer.cache_clear()

    try:
        yield prepared_test_database
    finally:
        _truncate_public_tables(prepared_test_database)
        _seed_default_workspace(prepared_test_database)
        object.__setattr__(settings, "topic_summarizer_backend", original_topic_summarizer_backend)
        object.__setattr__(settings, "analyzer_backend", original_analyzer_backend)
        object.__setattr__(settings, "stt_preload_on_startup", original_stt_preload_on_startup)
        object.__setattr__(settings, "persistence_backend", original_persistence_backend)
        object.__setattr__(settings, "postgresql_dsn", original_postgresql_dsn)
        object.__setattr__(settings, "redis_url", original_redis_url)
        persistence_module.get_postgresql_database.cache_clear()
        persistence_module.get_gpu_heavy_execution_gate.cache_clear()
        dependency_module._get_shared_analyzer.cache_clear()
        dependency_module._get_shared_topic_summarizer.cache_clear()


@pytest.fixture
def client(isolated_database):
    """FastAPI 테스트 클라이언트를 제공한다."""

    with TestClient(app) as test_client:
        yield test_client
