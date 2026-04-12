"""사내용 최소 인증 서비스."""

from __future__ import annotations

from server.app.domain.models.auth_session import (
    AuthenticatedSession,
    IssuedAuthSession,
)
from server.app.domain.models.user import UserAccount
from server.app.services.auth.helpers.normalization import (
    is_expired,
    normalize_client_type,
    normalize_display_name,
    normalize_login_id,
    normalize_optional_text,
    normalize_password,
    normalize_workspace_role,
    utc_now_iso,
)
from server.app.services.auth.helpers.passwords import (
    PasswordHashParts,
    hash_password,
    hash_token,
    parse_password_hash,
    verify_password,
)
from server.app.services.auth.service_flows import (
    authenticate,
    bootstrap_admin,
    change_workspace_member_role,
    create_workspace_user,
    issue_session,
    list_workspace_members,
    login,
    logout,
    provision_initial_admin,
)


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
        self._bootstrap_conflict_error_type = BootstrapConflictError
        self._inactive_user_error_type = InactiveUserError
        self._invalid_credentials_error_type = InvalidCredentialsError
        self._user_not_found_error_type = UserNotFoundError

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

        return bootstrap_admin(
            self,
            login_id=login_id,
            password=password,
            display_name=display_name,
            job_title=job_title,
            department=department,
            client_type=client_type,
        )

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

        return provision_initial_admin(
            self,
            login_id=login_id,
            password=password,
            display_name=display_name,
            job_title=job_title,
            department=department,
        )

    def login(
        self,
        *,
        login_id: str,
        password: str,
        client_type: str = "desktop",
    ) -> IssuedAuthSession:
        """로그인 아이디와 비밀번호로 로그인한다."""

        return login(
            self,
            login_id=login_id,
            password=password,
            client_type=client_type,
        )

    def authenticate(self, token: str) -> AuthenticatedSession | None:
        """Bearer 토큰으로 인증 세션을 확인한다."""

        return authenticate(self, token)

    def logout(self, session_id: str) -> None:
        """인증 세션을 만료 처리한다."""

        logout(self, session_id)

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

        return create_workspace_user(
            self,
            login_id=login_id,
            password=password,
            display_name=display_name,
            job_title=job_title,
            department=department,
            role=role,
        )

    def list_workspace_members(self) -> list[UserAccount]:
        """기본 워크스페이스 멤버 목록을 반환한다."""

        return list_workspace_members(self)

    def change_workspace_member_role(self, *, login_id: str, role: str) -> UserAccount:
        """기본 워크스페이스 멤버 역할을 변경한다."""

        return change_workspace_member_role(
            self,
            login_id=login_id,
            role=role,
        )

    def _issue_session(self, *, user: UserAccount, client_type: str) -> IssuedAuthSession:
        return issue_session(self, user=user, client_type=client_type)

    @classmethod
    def _hash_password(cls, password: str) -> str:
        return hash_password(
            password,
            password_normalizer=cls._normalize_password,
            algorithm=cls._PASSWORD_HASH_ALGORITHM,
            iterations=cls._PASSWORD_HASH_ITERATIONS,
        )

    @classmethod
    def _verify_password(cls, password: str, stored_hash: str) -> bool:
        return verify_password(
            password,
            stored_hash,
            password_normalizer=cls._normalize_password,
            algorithm=cls._PASSWORD_HASH_ALGORITHM,
            invalid_credentials_error_type=InvalidCredentialsError,
        )

    @classmethod
    def _parse_password_hash(cls, stored_hash: str) -> PasswordHashParts:
        return parse_password_hash(
            stored_hash,
            algorithm=cls._PASSWORD_HASH_ALGORITHM,
            invalid_credentials_error_type=InvalidCredentialsError,
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hash_token(token)

    @staticmethod
    def _normalize_login_id(login_id: str) -> str:
        return normalize_login_id(login_id)

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        return normalize_display_name(display_name)

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        return normalize_optional_text(value)

    @staticmethod
    def _normalize_client_type(client_type: str) -> str:
        return normalize_client_type(client_type)

    @staticmethod
    def _normalize_workspace_role(role: str) -> str:
        return normalize_workspace_role(role)

    @staticmethod
    def _normalize_password(password: str) -> str:
        return normalize_password(password)

    @staticmethod
    def _utc_now_iso() -> str:
        return utc_now_iso()

    @staticmethod
    def _is_expired(expires_at: str) -> bool:
        return is_expired(expires_at)
