"""인증 세션 엔티티."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from server.app.core.identifiers import generate_uuid_str

from server.app.domain.models.user import UserAccount


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuthSession:
    """서버 발급 인증 세션."""

    id: str
    user_id: str
    token_hash: str
    client_type: str
    created_at: str
    expires_at: str
    revoked_at: str | None = None
    last_seen_at: str | None = None

    @classmethod
    def issue(
        cls,
        *,
        user_id: str,
        token_hash: str,
        client_type: str,
        ttl_hours: int,
    ) -> "AuthSession":
        """지정한 TTL 기준으로 새 인증 세션을 발급한다."""

        now = _utc_now()
        return cls(
            id=generate_uuid_str(),
            user_id=user_id,
            token_hash=token_hash,
            client_type=client_type,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
        )


@dataclass(frozen=True)
class AuthenticatedSession:
    """인증된 사용자와 세션 컨텍스트."""

    user: UserAccount
    session: AuthSession


@dataclass(frozen=True)
class IssuedAuthSession:
    """클라이언트에 반환할 발급 결과."""

    user: UserAccount
    session: AuthSession
    access_token: str
