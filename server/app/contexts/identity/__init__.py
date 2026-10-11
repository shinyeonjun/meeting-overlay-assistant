"""신원(Identity) 바운디드 컨텍스트의 공개 API.

사용자, 로그인 세션, 요청 주체, 인증 유스케이스를 제공한다.
다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from server.app.contexts.identity.application import (
    AuthService,
    AuthServiceError,
    BootstrapConflictError,
    InactiveUserError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from server.app.contexts.identity.domain import (
    AuthenticatedRequest,
    IssuedLoginSession,
    LoginSession,
    UserAccount,
)

__all__ = [
    "AuthService",
    "AuthServiceError",
    "AuthenticatedRequest",
    "BootstrapConflictError",
    "InactiveUserError",
    "IssuedLoginSession",
    "InvalidCredentialsError",
    "LoginSession",
    "UserAccount",
    "UserNotFoundError",
]
