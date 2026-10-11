"""Alembic 실행 환경. DSN은 runner.build_alembic_config가 전달한다."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

dsn = context.config.attributes.get("dsn")
if not dsn:
    raise RuntimeError("마이그레이션 DSN이 없습니다. upgrade_database(dsn)으로 실행하세요.")

# 앱은 psycopg(v3)를 쓰므로 SQLAlchemy도 같은 드라이버를 쓰게 한다.
url = dsn.replace("postgresql://", "postgresql+psycopg://", 1)


def run_migrations_online() -> None:
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, transactional_ddl=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations_online()
