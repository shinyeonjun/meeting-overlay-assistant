"""인증 저장소 워크스페이스 헬퍼."""

from __future__ import annotations

from server.app.core.workspace_defaults import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    DEFAULT_WORKSPACE_STATUS,
)


def ensure_default_workspace(connection) -> None:
    """기본 워크스페이스가 없으면 생성한다."""

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

