"""마이그레이션을 코드에서 실행하는 진입점."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS_DIR = Path(__file__).resolve().parent


def build_alembic_config(dsn: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    # env.py가 이 값을 읽어 연결한다. alembic.ini 파일 없이 실행하기 위함이다.
    config.attributes["dsn"] = dsn
    return config


def upgrade_database(dsn: str, revision: str = "head") -> None:
    """DB를 지정 리비전(기본: 최신)까지 올린다."""

    command.upgrade(build_alembic_config(dsn), revision)
