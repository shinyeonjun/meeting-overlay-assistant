"""회의 맥락 라우트 공통 지원 함수."""

from server.app.api.http.schemas.context import (
    AccountResponse,
    ContactResponse,
    ContextThreadResponse,
)
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.models.auth_session import AuthenticatedSession


def resolve_workspace_id(auth_context: AuthenticatedSession | None) -> str:
    if auth_context is None:
        return DEFAULT_WORKSPACE_ID
    return auth_context.user.workspace_id or DEFAULT_WORKSPACE_ID


def to_account_response(item) -> AccountResponse:
    return AccountResponse(
        id=item.id,
        workspace_id=item.workspace_id,
        name=item.name,
        description=item.description,
        status=item.status,
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def to_contact_response(item) -> ContactResponse:
    return ContactResponse(
        id=item.id,
        workspace_id=item.workspace_id,
        account_id=item.account_id,
        name=item.name,
        email=item.email,
        job_title=item.job_title,
        department=item.department,
        notes=item.notes,
        status=item.status,
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def to_context_thread_response(item) -> ContextThreadResponse:
    return ContextThreadResponse(
        id=item.id,
        workspace_id=item.workspace_id,
        account_id=item.account_id,
        contact_id=item.contact_id,
        title=item.title,
        summary=item.summary,
        status=item.status,
        created_by_user_id=item.created_by_user_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
