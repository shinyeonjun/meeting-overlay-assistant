"""HTTP 계층에서 공통 관련 auth 구성을 담당한다."""
from pydantic import BaseModel, Field


class BootstrapAdminRequest(BaseModel):
    """초기 관리자 생성 요청."""

    login_id: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1)
    job_title: str | None = None
    department: str | None = None
    client_type: str = Field(default="desktop", min_length=1)


class LoginRequest(BaseModel):
    """로그인 요청."""

    login_id: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)
    client_type: str = Field(default="desktop", min_length=1)


class AuthUserResponse(BaseModel):
    """인증 사용자 응답."""

    id: str
    login_id: str
    display_name: str
    job_title: str | None = None
    department: str | None = None
    workspace_id: str | None = None
    workspace_name: str | None = None
    workspace_slug: str | None = None
    workspace_role: str | None = None
    workspace_status: str | None = None
    status: str
    created_at: str
    updated_at: str


class AuthSessionResponse(BaseModel):
    """세션 발급 응답."""

    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: AuthUserResponse


class AuthConfigResponse(BaseModel):
    """설치형 클라이언트용 인증 설정 응답."""

    enabled: bool
    bootstrap_required: bool
    user_count: int
