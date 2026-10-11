"""활성 계정 이름의 워크스페이스 내 중복을 막는다.

같은 워크스페이스에서 앞뒤 공백과 대소문자를 무시했을 때 같은 이름의 활성 계정은 하나만 허용한다.
동시 요청도 DB 제약으로 막는다. 기존 DB에 중복이 있으면 이 리비전은 실패하므로 먼저 정리해야 한다.

Revision ID: 0003_account_name_unique
Revises: 0002_session_runtime_heartbeat
Create Date: 2026-10-11
"""

from __future__ import annotations

from alembic import op

revision: str = "0003_account_name_unique"
down_revision: str | None = "0002_session_runtime_heartbeat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_workspace_name_active
            ON accounts (workspace_id, lower(btrim(name)))
            WHERE status = 'active';
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP INDEX IF EXISTS uq_accounts_workspace_name_active;")
