"""인증 저장소 사용자/멤버 쿼리."""

from __future__ import annotations

from server.app.core.workspace_defaults import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    DEFAULT_WORKSPACE_STATUS,
)
from server.app.domain.models.user import UserAccount
from server.app.infrastructure.persistence.postgresql.repositories.auth_helpers.workspace import (
    ensure_default_workspace,
)


def list_workspace_member_rows(connection, workspace_id: str):
    """워크스페이스 멤버 row 목록을 조회한다."""

    return connection.execute(
        """
        SELECT
            users.id,
            users.login_id,
            users.display_name,
            users.job_title,
            users.department,
            users.status,
            users.created_at,
            users.updated_at,
            workspaces.id AS workspace_id,
            workspaces.name AS workspace_name,
            workspaces.slug AS workspace_slug,
            workspaces.status AS workspace_status,
            workspace_members.workspace_role AS workspace_role
        FROM workspace_members
        INNER JOIN users ON users.id = workspace_members.user_id
        INNER JOIN workspaces ON workspaces.id = workspace_members.workspace_id
        WHERE workspace_members.workspace_id = %s
        ORDER BY
            CASE workspace_members.workspace_role
                WHEN 'owner' THEN 0
                WHEN 'admin' THEN 1
                WHEN 'member' THEN 2
                ELSE 3
            END,
            users.display_name ASC,
            users.login_id ASC
        """,
        (workspace_id,),
    ).fetchall()


def create_user_with_password(
    connection,
    *,
    user: UserAccount,
    password_hash: str,
    password_updated_at: str,
) -> UserAccount:
    """사용자, 비밀번호, 기본 워크스페이스 멤버십을 함께 생성한다."""

    ensure_default_workspace(connection)
    connection.execute(
        """
        INSERT INTO users (
            id,
            login_id,
            display_name,
            job_title,
            department,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user.id,
            user.login_id,
            user.display_name,
            user.job_title,
            user.department,
            user.status,
            user.created_at,
            user.updated_at,
        ),
    )
    connection.execute(
        """
        INSERT INTO auth_password_credentials (
            user_id,
            password_hash,
            password_updated_at
        )
        VALUES (%s, %s, %s)
        """,
        (
            user.id,
            password_hash,
            password_updated_at,
        ),
    )
    connection.execute(
        """
        INSERT INTO workspace_members (
            workspace_id,
            user_id,
            workspace_role,
            status,
            joined_at,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            DEFAULT_WORKSPACE_ID,
            user.id,
            user.workspace_role or "member",
            "active" if user.status == "active" else "inactive",
            user.created_at,
            user.created_at,
            user.updated_at,
        ),
    )
    return UserAccount(
        id=user.id,
        login_id=user.login_id,
        display_name=user.display_name,
        job_title=user.job_title,
        department=user.department,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
        workspace_id=DEFAULT_WORKSPACE_ID,
        workspace_name=DEFAULT_WORKSPACE_NAME,
        workspace_slug=DEFAULT_WORKSPACE_SLUG,
        workspace_role=user.workspace_role,
        workspace_status=DEFAULT_WORKSPACE_STATUS,
    )


def get_user_row_by_login_id(connection, login_id: str):
    """로그인 아이디 기준 사용자 row를 조회한다."""

    return connection.execute(
        """
        SELECT
            users.id,
            users.login_id,
            users.display_name,
            users.job_title,
            users.department,
            users.status,
            users.created_at,
            users.updated_at,
            workspaces.id AS workspace_id,
            workspaces.name AS workspace_name,
            workspaces.slug AS workspace_slug,
            workspaces.status AS workspace_status,
            workspace_members.workspace_role AS workspace_role
        FROM users
        INNER JOIN workspace_members
            ON workspace_members.user_id = users.id
           AND workspace_members.status = 'active'
        INNER JOIN workspaces
            ON workspaces.id = workspace_members.workspace_id
           AND workspaces.status = 'active'
        WHERE login_id = %s
        ORDER BY
            CASE workspace_members.workspace_role
                WHEN 'owner' THEN 0
                WHEN 'admin' THEN 1
                WHEN 'member' THEN 2
                ELSE 3
            END,
            workspaces.created_at ASC
        LIMIT 1
        """,
        (login_id,),
    ).fetchone()


def get_password_hash_row(connection, user_id: str):
    """사용자 비밀번호 해시 row를 조회한다."""

    return connection.execute(
        """
        SELECT password_hash
        FROM auth_password_credentials
        WHERE user_id = %s
        """,
        (user_id,),
    ).fetchone()


def update_workspace_member_role(
    connection,
    *,
    user_id: str,
    workspace_role: str,
    updated_at: str,
    workspace_id: str,
) -> None:
    """워크스페이스 멤버 역할과 사용자 수정 시각을 갱신한다."""

    connection.execute(
        """
        UPDATE workspace_members
        SET workspace_role = %s, updated_at = %s
        WHERE workspace_id = %s AND user_id = %s
        """,
        (workspace_role, updated_at, workspace_id, user_id),
    )
    connection.execute(
        """
        UPDATE users
        SET updated_at = %s
        WHERE id = %s
        """,
        (updated_at, user_id),
    )

