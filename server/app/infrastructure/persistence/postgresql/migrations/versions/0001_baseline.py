"""기준선: 현재 완전 스키마(runtime + pgvector).

이 리비전 이전의 스키마 파일(000/001/010)은 더 이상 직접 적용하지 않는다.
이후 스키마 변경은 이 리비전 위에 새 리비전으로 추가한다.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-11
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels = None
depends_on = None

BASELINE_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "020_runtime_with_pgvector_schema.sql"
)


def upgrade() -> None:
    sql_text = BASELINE_SQL_PATH.read_text(encoding="utf-8-sig")
    op.get_bind().exec_driver_sql(sql_text)


def downgrade() -> None:
    raise NotImplementedError("기준선 리비전은 되돌리지 않는다. DB를 새로 만들어야 한다.")
