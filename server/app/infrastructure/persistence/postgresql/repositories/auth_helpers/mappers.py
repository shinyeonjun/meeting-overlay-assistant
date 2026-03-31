"""인증 저장소 row 매퍼."""

from __future__ import annotations

from server.app.domain.models.auth_session import AuthSession, AuthenticatedSession
from server.app.domain.models.user import UserAccount


def to_user(row) -> UserAccount:
    """DB row를 사용자 도메인 모델로 변환한다."""

    return UserAccount(
        id=row["id"],
        login_id=row["login_id"],
        display_name=row["display_name"],
        job_title=row["job_title"],
        department=row["department"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        workspace_id=row["workspace_id"] if "workspace_id" in row else None,
        workspace_name=row["workspace_name"] if "workspace_name" in row else None,
        workspace_slug=row["workspace_slug"] if "workspace_slug" in row else None,
        workspace_role=row["workspace_role"] if "workspace_role" in row else None,
        workspace_status=row["workspace_status"] if "workspace_status" in row else None,
    )


def to_authenticated_session(row) -> AuthenticatedSession:
    """DB row를 인증 세션 컨텍스트로 변환한다."""

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

