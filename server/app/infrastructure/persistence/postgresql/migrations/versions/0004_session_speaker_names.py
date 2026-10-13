"""세션별 화자 이름 테이블 추가.

화자 분리는 "SPEAKER_00" 같은 라벨만 준다. 사용자가 회의 뒤에 라벨에 이름을 붙이면
여기에 저장하고, 발화 원문(utterances.speaker_label)은 그대로 둔다.
화자 라벨은 후처리를 다시 돌리면 바뀔 수 있으므로 이름을 붙인 시점의 transcript 버전을 함께 저장한다.

Revision ID: 0004_session_speaker_names
Revises: 0003_account_name_unique
Create Date: 2026-10-13
"""

from __future__ import annotations

from alembic import op

revision: str = "0004_session_speaker_names"
down_revision: str | None = "0003_account_name_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS session_speaker_names (
            session_id TEXT NOT NULL,
            speaker_label TEXT NOT NULL,
            display_name TEXT NOT NULL,
            transcript_version INTEGER NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (session_id, speaker_label),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP TABLE IF EXISTS session_speaker_names;")
