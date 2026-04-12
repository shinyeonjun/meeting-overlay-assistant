"""인증 영역의 sessions 서비스를 제공한다."""
from __future__ import annotations

import secrets

from server.app.domain.models.auth_session import AuthSession, IssuedAuthSession


def login(
    service,
    *,
    login_id: str,
    password: str,
    client_type: str = "desktop",
):
    """로그인 ID와 비밀번호로 로그인한다."""

    normalized_login_id = service._normalize_login_id(login_id)
    user = service._repository.get_user_by_login_id(normalized_login_id)
    if user is None:
        raise service._invalid_credentials_error_type(
            "로그인 아이디 또는 비밀번호가 올바르지 않습니다."
        )
    if user.status != "active":
        raise service._inactive_user_error_type("비활성화된 사용자입니다.")

    stored_password_hash = service._repository.get_password_hash_by_user_id(user.id)
    if stored_password_hash is None or not service._verify_password(password, stored_password_hash):
        raise service._invalid_credentials_error_type(
            "로그인 아이디 또는 비밀번호가 올바르지 않습니다."
        )

    return issue_session(service, user=user, client_type=client_type)


def authenticate(service, token: str):
    """Bearer 토큰으로 인증 세션을 확인한다."""

    normalized_token = token.strip()
    if not normalized_token:
        return None

    auth_context = service._repository.get_authenticated_session_by_token_hash(
        service._hash_token(normalized_token)
    )
    if auth_context is None:
        return None
    if auth_context.user.status != "active":
        return None
    if service._is_expired(auth_context.session.expires_at):
        service._repository.revoke_session(auth_context.session.id, service._utc_now_iso())
        return None

    service._repository.touch_session(auth_context.session.id, service._utc_now_iso())
    return auth_context


def logout(service, session_id: str) -> None:
    """인증 세션을 만료 처리한다."""

    service._repository.revoke_session(session_id, service._utc_now_iso())


def issue_session(service, *, user, client_type: str) -> IssuedAuthSession:
    """사용자에게 새 인증 세션을 발급한다."""

    access_token = secrets.token_urlsafe(32)
    session = AuthSession.issue(
        user_id=user.id,
        token_hash=service._hash_token(access_token),
        client_type=service._normalize_client_type(client_type),
        ttl_hours=service._session_ttl_hours,
    )
    service._repository.create_session(session)
    return IssuedAuthSession(user=user, session=session, access_token=access_token)
