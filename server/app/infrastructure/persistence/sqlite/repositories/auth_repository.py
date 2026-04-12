"""SQLite 인증 저장소 구현."""

from __future__ import annotations

import sqlite3

from server.app.core.workspace_defaults import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    DEFAULT_WORKSPACE_STATUS,
)
from server.app.domain.models.auth_session import AuthSession, AuthenticatedSession
from server.app.domain.models.user import UserAccount
from server.app.infrastructure.persistence.sqlite.database import Database


class SQLiteAuthRepository:
    """SQLite 기반 인증 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def count_users(self) -> int:
        with self._database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"]) if row is not None else 0

    def list_workspace_members(self, workspace_id: str = DEFAULT_WORKSPACE_ID) -> list[UserAccount]:
        with self._database.connect() as connection:
            rows = connection.execute(
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
                WHERE workspace_members.workspace_id = ?
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
        return [self._to_user(row) for row in rows]

    def create_user_with_password(
        self,
        *,
        user: UserAccount,
        password_hash: str,
        password_updated_at: str,
    ) -> UserAccount:
        try:
            with self._database.transaction() as connection:
                self._ensure_default_workspace(connection)
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                    VALUES (?, ?, ?)
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
                    VALUES (?, ?, ?, ?, ?, ?, ?)
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
        except sqlite3.IntegrityError as error:
            raise ValueError("이미 사용 중인 로그인 아이디입니다.") from error
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

    def get_user_by_login_id(self, login_id: str) -> UserAccount | None:
        with self._database.connect() as connection:
            row = connection.execute(
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
                WHERE login_id = ?
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
        if row is None:
            return None
        return self._to_user(row)

    def get_password_hash_by_user_id(self, user_id: str) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT password_hash
                FROM auth_password_credentials
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return row["password_hash"]

    def create_session(self, session: AuthSession) -> AuthSession:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_sessions (
                    id,
                    user_id,
                    token_hash,
                    client_type,
                    created_at,
                    expires_at,
                    revoked_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.user_id,
                    session.token_hash,
                    session.client_type,
                    session.created_at,
                    session.expires_at,
                    session.revoked_at,
                    session.last_seen_at,
                ),
            )
            connection.commit()
        return session

    def get_authenticated_session_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthenticatedSession | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    users.id AS user_id,
                    users.login_id AS user_login_id,
                    users.display_name AS user_display_name,
                    users.job_title AS user_job_title,
                    users.department AS user_department,
                    users.status AS user_status,
                    users.created_at AS user_created_at,
                    users.updated_at AS user_updated_at,
                    workspaces.id AS workspace_id,
                    workspaces.name AS workspace_name,
                    workspaces.slug AS workspace_slug,
                    workspaces.status AS workspace_status,
                    workspace_members.workspace_role AS workspace_role,
                    auth_sessions.id AS session_id,
                    auth_sessions.token_hash AS session_token_hash,
                    auth_sessions.client_type AS session_client_type,
                    auth_sessions.created_at AS session_created_at,
                    auth_sessions.expires_at AS session_expires_at,
                    auth_sessions.revoked_at AS session_revoked_at,
                    auth_sessions.last_seen_at AS session_last_seen_at
                FROM auth_sessions
                INNER JOIN users ON users.id = auth_sessions.user_id
                INNER JOIN workspace_members
                    ON workspace_members.user_id = users.id
                   AND workspace_members.status = 'active'
                INNER JOIN workspaces
                    ON workspaces.id = workspace_members.workspace_id
                   AND workspaces.status = 'active'
                WHERE auth_sessions.token_hash = ?
                  AND auth_sessions.revoked_at IS NULL
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
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        return AuthenticatedSession(
            user=UserAccount(
                id=row["user_id"],
                login_id=row["user_login_id"],
                display_name=row["user_display_name"],
                job_title=row["user_job_title"],
                department=row["user_department"],
                status=row["user_status"],
                created_at=row["user_created_at"],
                updated_at=row["user_updated_at"],
                workspace_id=row["workspace_id"],
                workspace_name=row["workspace_name"],
                workspace_slug=row["workspace_slug"],
                workspace_role=row["workspace_role"],
                workspace_status=row["workspace_status"],
            ),
            session=AuthSession(
                id=row["session_id"],
                user_id=row["user_id"],
                token_hash=row["session_token_hash"],
                client_type=row["session_client_type"],
                created_at=row["session_created_at"],
                expires_at=row["session_expires_at"],
                revoked_at=row["session_revoked_at"],
                last_seen_at=row["session_last_seen_at"],
            ),
        )

    def touch_session(self, session_id: str, last_seen_at: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE auth_sessions
                SET last_seen_at = ?
                WHERE id = ?
                """,
                (last_seen_at, session_id),
            )
            connection.commit()

    def update_workspace_member_role(
        self,
        *,
        user_id: str,
        workspace_role: str,
        updated_at: str,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE workspace_members
                SET workspace_role = ?, updated_at = ?
                WHERE workspace_id = ? AND user_id = ?
                """,
                (workspace_role, updated_at, workspace_id, user_id),
            )
            connection.execute(
                """
                UPDATE users
                SET updated_at = ?
                WHERE id = ?
                """,
                (updated_at, user_id),
            )
            connection.commit()

    def revoke_session(self, session_id: str, revoked_at: str) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = ?
                WHERE id = ?
                """,
                (revoked_at, session_id),
            )
            connection.commit()

    @staticmethod
    def _to_user(row: sqlite3.Row) -> UserAccount:
        return UserAccount(
            id=row["id"],
            login_id=row["login_id"],
            display_name=row["display_name"],
            job_title=row["job_title"],
            department=row["department"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            workspace_id=row["workspace_id"] if "workspace_id" in row.keys() else None,
            workspace_name=row["workspace_name"] if "workspace_name" in row.keys() else None,
            workspace_slug=row["workspace_slug"] if "workspace_slug" in row.keys() else None,
            workspace_role=row["workspace_role"] if "workspace_role" in row.keys() else None,
            workspace_status=row["workspace_status"] if "workspace_status" in row.keys() else None,
        )

    @staticmethod
    def _ensure_default_workspace(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT INTO workspaces (id, slug, name, status, created_at, updated_at)
            SELECT ?, ?, ?, ?, datetime('now'), datetime('now')
            WHERE NOT EXISTS (SELECT 1 FROM workspaces WHERE id = ?)
            """,
            (
                DEFAULT_WORKSPACE_ID,
                DEFAULT_WORKSPACE_SLUG,
                DEFAULT_WORKSPACE_NAME,
                DEFAULT_WORKSPACE_STATUS,
                DEFAULT_WORKSPACE_ID,
            ),
        )
