"""SQLite 마이그레이션 진입점."""

from server.app.infrastructure.persistence.sqlite.migrations.runner import (
    run_sqlite_migrations,
)

__all__ = ["run_sqlite_migrations"]
