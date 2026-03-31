"""PostgreSQL 인증 저장소 구현."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.models.auth_session import AuthSession, AuthenticatedSession
from server.app.domain.models.user import UserAccount
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories.auth_helpers.mappers import (
    to_authenticated_session,
    to_user,
)
from server.app.infrastructure.persistence.postgresql.repositories.auth_helpers.sessions import (
    create_session as create_auth_session,
    get_authenticated_session_row,
    revoke_session as revoke_auth_session,
    touch_session as touch_auth_session,
)
from server.app.infrastructure.persistence.postgresql.repositories.auth_helpers.users import (
    create_user_with_password as create_workspace_user_with_password,
    get_password_hash_row,
    get_user_row_by_login_id,
    list_workspace_member_rows,
    update_workspace_member_role as update_member_role,
)
from server.app.infrastructure.persistence.postgresql.repositories.auth_helpers.workspace import (
    ensure_default_workspace,
)


class PostgreSQLAuthRepository:
    """PostgreSQL 기반 인증 저장소."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def count_users(self) -> int:
        with self._database.transaction() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"]) if row is not None else 0

    def list_workspace_members(self, workspace_id: str = DEFAULT_WORKSPACE_ID) -> list[UserAccount]:
        with self._database.transaction() as connection:
            rows = list_workspace_member_rows(connection, workspace_id)
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
                return create_workspace_user_with_password(
                    connection,
                    user=user,
                    password_hash=password_hash,
                    password_updated_at=password_updated_at,
                )
        except Exception as error:
            if getattr(error, "sqlstate", None) == "23505":
                raise ValueError("이미 사용 중인 로그인 아이디입니다.") from error
            raise

    def get_user_by_login_id(self, login_id: str) -> UserAccount | None:
        with self._database.transaction() as connection:
            row = get_user_row_by_login_id(connection, login_id)
        return self._to_user(row) if row is not None else None

    def get_password_hash_by_user_id(self, user_id: str) -> str | None:
        with self._database.transaction() as connection:
            row = get_password_hash_row(connection, user_id)
        return row["password_hash"] if row is not None else None

    def create_session(self, session: AuthSession) -> AuthSession:
        with self._database.transaction() as connection:
            return create_auth_session(connection, session)

    def get_authenticated_session_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthenticatedSession | None:
        with self._database.transaction() as connection:
            row = get_authenticated_session_row(connection, token_hash)
        return None if row is None else to_authenticated_session(row)

    def touch_session(self, session_id: str, last_seen_at: str) -> None:
        with self._database.transaction() as connection:
            touch_auth_session(connection, session_id, last_seen_at)

    def update_workspace_member_role(
        self,
        *,
        user_id: str,
        workspace_role: str,
        updated_at: str,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> None:
        with self._database.transaction() as connection:
            update_member_role(
                connection,
                user_id=user_id,
                workspace_role=workspace_role,
                updated_at=updated_at,
                workspace_id=workspace_id,
            )

    def revoke_session(self, session_id: str, revoked_at: str) -> None:
        with self._database.transaction() as connection:
            revoke_auth_session(connection, session_id, revoked_at)

    @staticmethod
    def _to_user(row) -> UserAccount:
        return to_user(row)

    @staticmethod
    def _ensure_default_workspace(connection) -> None:
        ensure_default_workspace(connection)
