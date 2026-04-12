"""세션용 맥락 정합성 해결 서비스."""

from __future__ import annotations

from server.app.domain.context import ResolvedMeetingContext
from server.app.services.context.context_catalog_service import ContextCatalogService


class ContextResolutionService:
    """Account / Contact / Thread 조합의 정합성을 맞춘다."""

    def __init__(self, catalog_service: ContextCatalogService) -> None:
        self._catalog_service = catalog_service

    def resolve_session_context(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> ResolvedMeetingContext:
        resolved_account_id = account_id
        resolved_contact_id = contact_id
        resolved_thread_id = context_thread_id

        contact = None
        if resolved_contact_id is not None:
            contact = self._catalog_service.require_contact(
                workspace_id=workspace_id,
                contact_id=resolved_contact_id,
            )
            if resolved_account_id is None:
                resolved_account_id = contact.account_id
            elif contact.account_id and contact.account_id != resolved_account_id:
                raise ValueError("상대방과 회사 연결 정보가 서로 맞지 않습니다.")

        if resolved_thread_id is not None:
            thread = self._catalog_service.require_context_thread(
                workspace_id=workspace_id,
                thread_id=resolved_thread_id,
            )
            if resolved_account_id is None:
                resolved_account_id = thread.account_id
            elif thread.account_id and thread.account_id != resolved_account_id:
                raise ValueError("스레드의 회사 연결 정보가 서로 맞지 않습니다.")
            if resolved_contact_id is None:
                resolved_contact_id = thread.contact_id
            elif thread.contact_id and thread.contact_id != resolved_contact_id:
                raise ValueError("스레드의 상대방 연결 정보가 서로 맞지 않습니다.")

        if resolved_account_id is not None:
            self._catalog_service.require_account(
                workspace_id=workspace_id,
                account_id=resolved_account_id,
            )

        if resolved_contact_id is not None and contact is None:
            self._catalog_service.require_contact(
                workspace_id=workspace_id,
                contact_id=resolved_contact_id,
            )

        return ResolvedMeetingContext(
            account_id=resolved_account_id,
            contact_id=resolved_contact_id,
            context_thread_id=resolved_thread_id,
        )
