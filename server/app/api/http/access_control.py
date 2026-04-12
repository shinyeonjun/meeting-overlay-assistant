"""HTTP 계층에서 공통 관련 access control 구성을 담당한다."""
from __future__ import annotations

from fastapi import HTTPException, status

from server.app.api.http.dependencies import get_session_service
from server.app.core.workspace_roles import ADMIN_WORKSPACE_ROLES
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.domain.session import MeetingSession

def is_admin_user(auth_context: AuthenticatedSession | None) -> bool:
    """전체 조회가 가능한 관리자 권한인지 확인한다."""

    if auth_context is None:
        return False
    workspace_role = auth_context.user.workspace_role
    return workspace_role in ADMIN_WORKSPACE_ROLES if workspace_role is not None else False


def resolve_scope_owner_id(
    scope: str,
    auth_context: AuthenticatedSession | None,
) -> str | None:
    """조회 scope를 실제 사용자 필터 값으로 해석한다."""

    normalized_scope = scope.strip().lower()
    if normalized_scope not in {"mine", "all"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 scope입니다. mine 또는 all만 사용할 수 있습니다.",
        )

    if auth_context is None:
        return None

    if normalized_scope == "mine":
        return auth_context.user.id

    if is_admin_user(auth_context):
        return None

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="전체 목록 조회는 owner 또는 admin만 사용할 수 있습니다.",
    )


def get_accessible_session_or_raise(
    session_id: str,
    auth_context: AuthenticatedSession | None,
) -> MeetingSession:
    """현재 사용자에게 접근 가능한 세션인지 검증하고 반환한다."""

    session = get_session_service().get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다.",
        )
    if not can_access_session(session, auth_context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 세션에 접근할 권한이 없습니다.",
        )
    return session


def can_access_session(
    session: MeetingSession,
    auth_context: AuthenticatedSession | None,
) -> bool:
    """세션 접근 가능 여부를 반환한다."""

    if auth_context is None:
        return True
    if is_admin_user(auth_context):
        return True
    return session.created_by_user_id == auth_context.user.id
