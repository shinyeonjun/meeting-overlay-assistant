"""세션 런타임 하트비트 열 추가.

control API와 live API가 분리된 배포에서는 live 프로세스의 메모리(WebSocket 컨텍스트)를
다른 프로세스가 볼 수 없다. live 프로세스가 진행 중인 세션의 하트비트를 DB에 찍고,
복구 서비스는 하트비트가 오래된 running 세션만 고아로 본다.

Revision ID: 0002_session_runtime_heartbeat
Revises: 0001_baseline
Create Date: 2026-10-11
"""

from __future__ import annotations

from alembic import op

revision: str = "0002_session_runtime_heartbeat"
down_revision: str | None = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS runtime_heartbeat_at TIMESTAMPTZ;
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "ALTER TABLE sessions DROP COLUMN IF EXISTS runtime_heartbeat_at;"
    )
