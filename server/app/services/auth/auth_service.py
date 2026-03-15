"""사내용 최소 인증 서비스."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from server.app.core.workspace_roles import VALID_WORKSPACE_ROLES
from server.app.domain.models.auth_session import (
    AuthSession,
    AuthenticatedSession,
    IssuedAuthSession,
)
from server.app.domain.models.user import UserAccount


class AuthServiceError(Exception):
    """인증 서비스 공통 예외."""


class BootstrapConflictError(AuthServiceError):
    """초기 관리자 생성 충돌."""


class InvalidCredentialsError(AuthServiceError):
    """잘못된 로그인 정보."""


class InactiveUserError(AuthServiceError):
    """비활성 사용자 접근."""


class UserNotFoundError(AuthServiceError):
    """대상 사용자를 찾지 못한 경우."""


@dataclass(frozen=True)
class PasswordHashParts:
    """저장용 비밀번호 해시 구성 요소."""

    iterations: int
    salt: bytes
    digest: bytes


class AuthService:
    """비밀번호 로그인과 서버 세션 발급을 담당한다."""

    _PASSWORD_HASH_ALGORITHM = "sha256"
    _PASSWORD_HASH_ITERATIONS = 390000

    def __init__(
        self,
        *,
        repository,
        session_ttl_hours: int,
    ) -> None:
        self._repository = repository
        self._session_ttl_hours = session_ttl_hours

    def bootstrap_admin(
        self,
        *,
        login_id: str,
        password: str,
        display_name: str,
        job_title: str | None = None,
        department: str | None = None,
        client_type: str = "desktop",
    ) -> IssuedAuthSession:
        """첫 관리자 계정을 생성하고 즉시 로그인 세션을 발급한다."""

        user = self.provision_initial_admin(
            login_id=login_id,
            password=password,
            display_name=display_name,
            job_title=job_title,
            department=department,
        )
        return self._issue_session(user=user, client_type=client_type)

    def provision_initial_admin(
        self,
        *,
        login_id: str,
        password: str,
        display_name: str,
        job_title: str | None = None,
        department: str | None = None,
    ) -> UserAccount:
        """초기 관리자 계정을 생성하되 로그인 세션은 발급하지 않는다."""

        if self._repository.count_users() > 0:
            raise BootstrapConflictError("초기 관리자 계정은 한 번만 생성할 수 있습니다.")

        user = UserAccount.create(
            login_id=self._normalize_login_id(login_id),
            display_name=self._normalize_display_name(display_name),
            job_title=self._normalize_optional_text(job_title),
            department=self._normalize_optional_text(department),
            workspace_role="owner",
        )
        password_hash = self._hash_password(password)
        user = self._repository.create_user_with_password(
            user=user,
            password_hash=password_hash,
            password_updated_at=self._utc_now_iso(),
        )
        return user

    def login(
        self,
        *,
        login_id: str,
        password: str,
        client_type: str = "desktop",
    ) -> IssuedAuthSession:
        """로그인 아이디와 비밀번호로 로그인한다."""

        normalized_login_id = self._normalize_login_id(login_id)
        user = self._repository.get_user_by_login_id(normalized_login_id)
        if user is None:
            raise InvalidCredentialsError("로그인 아이디 또는 비밀번호가 올바르지 않습니다.")
        if user.status != "active":
            raise InactiveUserError("비활성화된 사용자입니다.")

        stored_password_hash = self._repository.get_password_hash_by_user_id(user.id)
        if stored_password_hash is None or not self._verify_password(password, stored_password_hash):
            raise InvalidCredentialsError("로그인 아이디 또는 비밀번호가 올바르지 않습니다.")
        return self._issue_session(user=user, client_type=client_type)

    def authenticate(self, token: str) -> AuthenticatedSession | None:
        """Bearer 토큰으로 인증 세션을 확인한다."""

        normalized_token = token.strip()
        if not normalized_token:
            return None

        auth_context = self._repository.get_authenticated_session_by_token_hash(
            self._hash_token(normalized_token)
        )
        if auth_context is None:
            return None
        if auth_context.user.status != "active":
            return None
        if self._is_expired(auth_context.session.expires_at):
            self._repository.revoke_session(auth_context.session.id, self._utc_now_iso())
            return None

        self._repository.touch_session(auth_context.session.id, self._utc_now_iso())
        return auth_context

    def logout(self, session_id: str) -> None:
        """인증 세션을 만료 처리한다."""

        self._repository.revoke_session(session_id, self._utc_now_iso())

    def count_users(self) -> int:
        """현재 등록된 사용자 수를 반환한다."""

        return self._repository.count_users()

    def create_workspace_user(
        self,
        *,
        login_id: str,
        password: str,
        display_name: str,
        job_title: str | None = None,
        department: str | None = None,
        role: str = "member",
    ) -> UserAccount:
        """기본 워크스페이스 멤버를 생성한다."""

        normalized_role = self._normalize_workspace_role(role)
        user = UserAccount.create(
            login_id=self._normalize_login_id(login_id),
            display_name=self._normalize_display_name(display_name),
            job_title=self._normalize_optional_text(job_title),
            department=self._normalize_optional_text(department),
            workspace_role=normalized_role,
        )
        password_hash = self._hash_password(password)
        return self._repository.create_user_with_password(
            user=user,
            password_hash=password_hash,
            password_updated_at=self._utc_now_iso(),
        )

    def list_workspace_members(self) -> list[UserAccount]:
        """기본 워크스페이스 멤버 목록을 반환한다."""

        return self._repository.list_workspace_members()

    def change_workspace_member_role(self, *, login_id: str, role: str) -> UserAccount:
        """기본 워크스페이스 멤버 역할을 변경한다."""

        normalized_login_id = self._normalize_login_id(login_id)
        normalized_role = self._normalize_workspace_role(role)
        user = self._repository.get_user_by_login_id(normalized_login_id)
        if user is None:
            raise UserNotFoundError("대상 사용자를 찾지 못했습니다.")

        self._repository.update_workspace_member_role(
            user_id=user.id,
            workspace_role=normalized_role,
            updated_at=self._utc_now_iso(),
        )
        updated_user = self._repository.get_user_by_login_id(normalized_login_id)
        if updated_user is None:
            raise UserNotFoundError("역할 변경 후 사용자 정보를 다시 불러오지 못했습니다.")
        return updated_user

    def _issue_session(self, *, user: UserAccount, client_type: str) -> IssuedAuthSession:
        access_token = secrets.token_urlsafe(32)
        session = AuthSession.issue(
            user_id=user.id,
            token_hash=self._hash_token(access_token),
            client_type=self._normalize_client_type(client_type),
            ttl_hours=self._session_ttl_hours,
        )
        self._repository.create_session(session)
        return IssuedAuthSession(user=user, session=session, access_token=access_token)

    @classmethod
    def _hash_password(cls, password: str) -> str:
        normalized_password = cls._normalize_password(password)
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            cls._PASSWORD_HASH_ALGORITHM,
            normalized_password.encode("utf-8"),
            salt,
            cls._PASSWORD_HASH_ITERATIONS,
        )
        salt_b64 = base64.b64encode(salt).decode("ascii")
        digest_b64 = base64.b64encode(digest).decode("ascii")
        return (
            f"pbkdf2_{cls._PASSWORD_HASH_ALGORITHM}"
            f"${cls._PASSWORD_HASH_ITERATIONS}${salt_b64}${digest_b64}"
        )

    @classmethod
    def _verify_password(cls, password: str, stored_hash: str) -> bool:
        normalized_password = cls._normalize_password(password)
        parts = cls._parse_password_hash(stored_hash)
        computed_digest = hashlib.pbkdf2_hmac(
            cls._PASSWORD_HASH_ALGORITHM,
            normalized_password.encode("utf-8"),
            parts.salt,
            parts.iterations,
        )
        return hmac.compare_digest(parts.digest, computed_digest)

    @classmethod
    def _parse_password_hash(cls, stored_hash: str) -> PasswordHashParts:
        try:
            algorithm, raw_iterations, raw_salt, raw_digest = stored_hash.split("$", maxsplit=3)
        except ValueError as error:
            raise InvalidCredentialsError("저장된 비밀번호 해시 형식이 올바르지 않습니다.") from error
        if algorithm != f"pbkdf2_{cls._PASSWORD_HASH_ALGORITHM}":
            raise InvalidCredentialsError("지원하지 않는 비밀번호 해시 알고리즘입니다.")
        return PasswordHashParts(
            iterations=int(raw_iterations),
            salt=base64.b64decode(raw_salt.encode("ascii")),
            digest=base64.b64decode(raw_digest.encode("ascii")),
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_login_id(login_id: str) -> str:
        normalized = login_id.strip().lower()
        if not normalized:
            raise ValueError("로그인 아이디는 비워둘 수 없습니다.")
        return normalized

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        normalized = display_name.strip()
        if not normalized:
            raise ValueError("이름은 비워둘 수 없습니다.")
        return normalized

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_client_type(client_type: str) -> str:
        normalized = client_type.strip()
        return normalized or "desktop"

    @staticmethod
    def _normalize_workspace_role(role: str) -> str:
        normalized = role.strip().lower()
        if normalized not in VALID_WORKSPACE_ROLES:
            raise ValueError(
                f"지원하지 않는 역할입니다. 사용 가능한 값: {', '.join(VALID_WORKSPACE_ROLES)}"
            )
        return normalized

    @staticmethod
    def _normalize_password(password: str) -> str:
        if len(password) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        return password

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_expired(expires_at: str) -> bool:
        expires_at_value = datetime.fromisoformat(expires_at)
        return expires_at_value <= datetime.now(timezone.utc)
