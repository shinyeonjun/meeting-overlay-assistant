"""HTTP 계층에서 공통 관련 context 구성을 담당한다."""
from pydantic import BaseModel, Field


class AccountCreateRequest(BaseModel):
    """회사/거래처 생성 요청."""

    name: str = Field(..., min_length=1)
    description: str | None = None


class AccountResponse(BaseModel):
    """회사/거래처 응답."""

    id: str
    workspace_id: str
    name: str
    description: str | None = None
    status: str
    created_by_user_id: str | None = None
    created_at: str
    updated_at: str


class AccountListResponse(BaseModel):
    """회사/거래처 목록 응답."""

    items: list[AccountResponse]


class ContactCreateRequest(BaseModel):
    """상대방 생성 요청."""

    name: str = Field(..., min_length=1)
    account_id: str | None = None
    email: str | None = None
    job_title: str | None = None
    department: str | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    """상대방 응답."""

    id: str
    workspace_id: str
    account_id: str | None = None
    name: str
    email: str | None = None
    job_title: str | None = None
    department: str | None = None
    notes: str | None = None
    status: str
    created_by_user_id: str | None = None
    created_at: str
    updated_at: str


class ContactListResponse(BaseModel):
    """상대방 목록 응답."""

    items: list[ContactResponse]


class ContextThreadCreateRequest(BaseModel):
    """업무 흐름 생성 요청."""

    title: str = Field(..., min_length=1)
    account_id: str | None = None
    contact_id: str | None = None
    summary: str | None = None


class ContextThreadResponse(BaseModel):
    """업무 흐름 응답."""

    id: str
    workspace_id: str
    account_id: str | None = None
    contact_id: str | None = None
    title: str
    summary: str | None = None
    status: str
    created_by_user_id: str | None = None
    created_at: str
    updated_at: str


class ContextThreadListResponse(BaseModel):
    """업무 흐름 목록 응답."""

    items: list[ContextThreadResponse]

