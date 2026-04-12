"""기존 meeting_context_service 경로 호환 facade."""

from __future__ import annotations

from server.app.domain.context import AccountContext, ContactContext, ContextThread
from server.app.services.context.context_catalog_service import ContextCatalogService
from server.app.services.context.context_resolution_service import ContextResolutionService


class MeetingContextService:
    """기존 호출자를 위한 맥락 facade."""

    def __init__(self, repository) -> None:
        self._catalog_service = ContextCatalogService(repository)
        self._resolution_service = ContextResolutionService(self._catalog_service)

    def create_account(
        self,
        *,
        workspace_id: str,
        name: str,
        description: str | None = None,
        created_by_user_id: str | None = None,
    ) -> AccountContext:
        return self._catalog_service.create_account(
            workspace_id=workspace_id,
            name=name,
            description=description,
            created_by_user_id=created_by_user_id,
        )

    def list_accounts(self, *, workspace_id: str, limit: int = 100) -> list[AccountContext]:
        return self._catalog_service.list_accounts(workspace_id=workspace_id, limit=limit)

    def create_contact(
        self,
        *,
        workspace_id: str,
        name: str,
        account_id: str | None = None,
        email: str | None = None,
        job_title: str | None = None,
        department: str | None = None,
        notes: str | None = None,
        created_by_user_id: str | None = None,
    ) -> ContactContext:
        return self._catalog_service.create_contact(
            workspace_id=workspace_id,
            name=name,
            account_id=account_id,
            email=email,
            job_title=job_title,
            department=department,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )

    def list_contacts(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[ContactContext]:
        return self._catalog_service.list_contacts(
            workspace_id=workspace_id,
            account_id=account_id,
            limit=limit,
        )

    def create_context_thread(
        self,
        *,
        workspace_id: str,
        title: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        summary: str | None = None,
        created_by_user_id: str | None = None,
    ) -> ContextThread:
        return self._catalog_service.create_context_thread(
            workspace_id=workspace_id,
            title=title,
            account_id=account_id,
            contact_id=contact_id,
            summary=summary,
            created_by_user_id=created_by_user_id,
        )

    def list_context_threads(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        limit: int = 100,
    ) -> list[ContextThread]:
        return self._catalog_service.list_context_threads(
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            limit=limit,
        )

    def resolve_session_context(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> dict[str, str | None]:
        return self._resolution_service.resolve_session_context(
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
        ).as_dict()
