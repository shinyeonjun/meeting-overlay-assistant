"""인증 영역의 bootstrap 서비스를 제공한다."""
from __future__ import annotations

from server.app.domain.models.user import UserAccount


def bootstrap_admin(
    service,
    *,
    login_id: str,
    password: str,
    display_name: str,
    job_title: str | None = None,
    department: str | None = None,
    client_type: str = "desktop",
):
    """첫 관리자 계정 생성 후 즉시 세션을 발급한다."""

    user = provision_initial_admin(
        service,
        login_id=login_id,
        password=password,
        display_name=display_name,
        job_title=job_title,
        department=department,
    )
    return service._issue_session(user=user, client_type=client_type)


def provision_initial_admin(
    service,
    *,
    login_id: str,
    password: str,
    display_name: str,
    job_title: str | None = None,
    department: str | None = None,
) -> UserAccount:
    """초기 관리자 계정을 만들고 로그인 세션은 발급하지 않는다."""

    if service._repository.count_users() > 0:
        raise service._bootstrap_conflict_error_type(
            "초기 관리자 계정은 한 번만 생성할 수 있습니다."
        )

    user = UserAccount.create(
        login_id=service._normalize_login_id(login_id),
        display_name=service._normalize_display_name(display_name),
        job_title=service._normalize_optional_text(job_title),
        department=service._normalize_optional_text(department),
        workspace_role="owner",
    )
    return service._repository.create_user_with_password(
        user=user,
        password_hash=service._hash_password(password),
        password_updated_at=service._utc_now_iso(),
    )
