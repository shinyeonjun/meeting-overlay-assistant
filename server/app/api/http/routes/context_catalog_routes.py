"""회의 맥락 카탈로그 라우트."""

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.dependencies import get_context_catalog_service
from server.app.api.http.routes.context_route_support import (
    resolve_workspace_id,
    to_account_response,
    to_contact_response,
    to_context_thread_response,
)
from server.app.api.http.schemas.context import (
    AccountCreateRequest,
    AccountListResponse,
    AccountResponse,
    ContactCreateRequest,
    ContactListResponse,
    ContactResponse,
    ContextThreadCreateRequest,
    ContextThreadListResponse,
    ContextThreadResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(
    limit: int = 100,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> AccountListResponse:
    items = get_context_catalog_service().list_accounts(
        workspace_id=resolve_workspace_id(auth_context),
        limit=max(1, min(limit, 200)),
    )
    return AccountListResponse(items=[to_account_response(item) for item in items])


@router.post("/accounts", response_model=AccountResponse)
def create_account(
    request: AccountCreateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> AccountResponse:
    try:
        item = get_context_catalog_service().create_account(
            workspace_id=resolve_workspace_id(auth_context),
            name=request.name,
            description=request.description,
            created_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return to_account_response(item)


@router.get("/contacts", response_model=ContactListResponse)
def list_contacts(
    account_id: str | None = None,
    limit: int = 100,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ContactListResponse:
    try:
        items = get_context_catalog_service().list_contacts(
            workspace_id=resolve_workspace_id(auth_context),
            account_id=account_id,
            limit=max(1, min(limit, 200)),
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ContactListResponse(items=[to_contact_response(item) for item in items])


@router.post("/contacts", response_model=ContactResponse)
def create_contact(
    request: ContactCreateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ContactResponse:
    try:
        item = get_context_catalog_service().create_contact(
            workspace_id=resolve_workspace_id(auth_context),
            account_id=request.account_id,
            name=request.name,
            email=request.email,
            job_title=request.job_title,
            department=request.department,
            notes=request.notes,
            created_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return to_contact_response(item)


@router.get("/threads", response_model=ContextThreadListResponse)
def list_context_threads(
    account_id: str | None = None,
    contact_id: str | None = None,
    limit: int = 100,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ContextThreadListResponse:
    try:
        items = get_context_catalog_service().list_context_threads(
            workspace_id=resolve_workspace_id(auth_context),
            account_id=account_id,
            contact_id=contact_id,
            limit=max(1, min(limit, 200)),
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ContextThreadListResponse(items=[to_context_thread_response(item) for item in items])


@router.post("/threads", response_model=ContextThreadResponse)
def create_context_thread(
    request: ContextThreadCreateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ContextThreadResponse:
    try:
        item = get_context_catalog_service().create_context_thread(
            workspace_id=resolve_workspace_id(auth_context),
            title=request.title,
            account_id=request.account_id,
            contact_id=request.contact_id,
            summary=request.summary,
            created_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return to_context_thread_response(item)
