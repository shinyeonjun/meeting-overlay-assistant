"""인증 영역의 workspace 서비스를 제공한다."""
from __future__ import annotations

from server.app.domain.models.user import UserAccount


def create_workspace_user(
    service,
    *,
    login_id: str,
    password: str,
    display_name: str,
    job_title: str | None = None,
    department: str | None = None,
    role: str = "member",
) -> UserAccount:
    """기본 워크스페이스 멤버를 생성한다."""

    user = UserAccount.create(
        login_id=service._normalize_login_id(login_id),
        display_name=service._normalize_display_name(display_name),
        job_title=service._normalize_optional_text(job_title),
        department=service._normalize_optional_text(department),
        workspace_role=service._normalize_workspace_role(role),
    )
    return service._repository.create_user_with_password(
        user=user,
        password_hash=service._hash_password(password),
        password_updated_at=service._utc_now_iso(),
    )


def list_workspace_members(service) -> list[UserAccount]:
    """기본 워크스페이스 멤버 목록을 반환한다."""

    return service._repository.list_workspace_members()


def change_workspace_member_role(service, *, login_id: str, role: str) -> UserAccount:
    """기본 워크스페이스 멤버 역할을 변경한다."""

    normalized_login_id = service._normalize_login_id(login_id)
    user = service._repository.get_user_by_login_id(normalized_login_id)
    if user is None:
        raise service._user_not_found_error_type("대상 사용자를 찾지 못했습니다.")

    service._repository.update_workspace_member_role(
        user_id=user.id,
        workspace_role=service._normalize_workspace_role(role),
        updated_at=service._utc_now_iso(),
    )
    updated_user = service._repository.get_user_by_login_id(normalized_login_id)
    if updated_user is None:
        raise service._user_not_found_error_type(
            "역할 변경 후 사용자 정보를 다시 불러오지 못했습니다."
        )
    return updated_user
