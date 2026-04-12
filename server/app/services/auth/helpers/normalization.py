"""인증 영역의 normalization 서비스를 제공한다."""
from __future__ import annotations

from datetime import datetime, timezone

from server.app.core.workspace_roles import VALID_WORKSPACE_ROLES


def normalize_login_id(login_id: str) -> str:
    """로그인 아이디를 정규화한다."""

    normalized = login_id.strip().lower()
    if not normalized:
        raise ValueError("로그인 아이디는 비워둘 수 없습니다.")
    return normalized


def normalize_display_name(display_name: str) -> str:
    """표시 이름을 정규화한다."""

    normalized = display_name.strip()
    if not normalized:
        raise ValueError("이름은 비워둘 수 없습니다.")
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    """선택 텍스트 필드를 정규화한다."""

    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_client_type(client_type: str) -> str:
    """클라이언트 타입을 정규화한다."""

    normalized = client_type.strip()
    return normalized or "desktop"


def normalize_workspace_role(role: str) -> str:
    """워크스페이스 역할을 검증하고 정규화한다."""

    normalized = role.strip().lower()
    if normalized not in VALID_WORKSPACE_ROLES:
        raise ValueError(
            f"지원하지 않는 역할입니다. 사용 가능한 값: {', '.join(VALID_WORKSPACE_ROLES)}"
        )
    return normalized


def normalize_password(password: str) -> str:
    """비밀번호 입력을 검증한다."""

    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")
    return password


def utc_now_iso() -> str:
    """현재 UTC 시간을 ISO 문자열로 반환한다."""

    return datetime.now(timezone.utc).isoformat()


def is_expired(expires_at: str) -> bool:
    """만료 시각이 지났는지 확인한다."""

    expires_at_value = datetime.fromisoformat(expires_at)
    return expires_at_value <= datetime.now(timezone.utc)

