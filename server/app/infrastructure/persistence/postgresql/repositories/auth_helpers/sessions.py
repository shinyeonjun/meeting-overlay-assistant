"""인증 저장소 세션 쿼리."""

from __future__ import annotations

from server.app.domain.models.auth_session import AuthSession


def create_session(connection, session: AuthSession) -> AuthSession:
    """인증 세션을 저장한다."""

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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
    return session


def get_authenticated_session_row(connection, token_hash: str):
    """토큰 해시 기준 인증 세션 row를 조회한다."""

    return connection.execute(
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
        WHERE auth_sessions.token_hash = %s
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


def touch_session(connection, session_id: str, last_seen_at: str) -> None:
    """세션 마지막 사용 시각을 갱신한다."""

    connection.execute(
        """
        UPDATE auth_sessions
        SET last_seen_at = %s
        WHERE id = %s
        """,
        (last_seen_at, session_id),
    )


def revoke_session(connection, session_id: str, revoked_at: str) -> None:
    """세션을 만료 처리한다."""

    connection.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = %s
        WHERE id = %s
        """,
        (revoked_at, session_id),
    )
