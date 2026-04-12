"""HTTP 계층에서 공통 관련 auth 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from server.app.api.http.dependencies import get_auth_service
from server.app.api.http.schemas.auth import (
    AuthConfigResponse,
    AuthSessionResponse,
    AuthUserResponse,
    BootstrapAdminRequest,
    LoginRequest,
)
from server.app.api.http.security import require_authenticated_session
from server.app.core.config import settings
from server.app.domain.models.auth_session import AuthenticatedSession, IssuedAuthSession
from server.app.domain.models.user import UserAccount
from server.app.services.auth.auth_service import (
    BootstrapConflictError,
    InactiveUserError,
    InvalidCredentialsError,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _to_user_response(user: UserAccount) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        login_id=user.login_id,
        display_name=user.display_name,
        job_title=user.job_title,
        department=user.department,
        workspace_id=user.workspace_id,
        workspace_name=user.workspace_name,
        workspace_slug=user.workspace_slug,
        workspace_role=user.workspace_role,
        workspace_status=user.workspace_status,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _to_session_response(issued: IssuedAuthSession) -> AuthSessionResponse:
    return AuthSessionResponse(
        access_token=issued.access_token,
        expires_at=issued.session.expires_at,
        user=_to_user_response(issued.user),
    )


@router.get("/config", response_model=AuthConfigResponse)
def get_auth_config() -> AuthConfigResponse:
    """설치형 클라이언트가 인증 모드를 파악할 수 있게 한다."""

    auth_service = get_auth_service()
    user_count = auth_service.count_users()
    return AuthConfigResponse(
        enabled=settings.auth_enabled,
        bootstrap_required=user_count == 0,
        user_count=user_count,
    )


@router.post("/bootstrap-admin", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(request: BootstrapAdminRequest) -> AuthSessionResponse:
    """첫 관리자 계정을 생성한다."""

    auth_service = get_auth_service()
    try:
        issued = auth_service.bootstrap_admin(
            login_id=request.login_id,
            password=request.password,
            display_name=request.display_name,
            job_title=request.job_title,
            department=request.department,
            client_type=request.client_type,
        )
    except BootstrapConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _to_session_response(issued)


@router.post("/login", response_model=AuthSessionResponse)
def login(request: LoginRequest) -> AuthSessionResponse:
    """로그인 아이디와 비밀번호로 로그인한다."""

    auth_service = get_auth_service()
    try:
        issued = auth_service.login(
            login_id=request.login_id,
            password=request.password,
            client_type=request.client_type,
        )
    except InactiveUserError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _to_session_response(issued)


@router.get("/me", response_model=AuthUserResponse)
def get_me(
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> AuthUserResponse:
    """현재 인증된 사용자를 반환한다."""

    if auth_context is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 기능이 비활성화되어 있습니다.",
        )
    return _to_user_response(auth_context.user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> Response:
    """현재 인증 세션을 종료한다."""

    if auth_context is None and not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 기능이 비활성화되어 있습니다.",
        )
    if auth_context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    get_auth_service().logout(auth_context.session.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
