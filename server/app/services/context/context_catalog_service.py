"""Account / Contact / Thread 정본 관리 서비스."""

from __future__ import annotations

from server.app.domain.context import AccountContext, ContactContext, ContextThread


class ContextCatalogService:
    """맥락 정본 CRUD와 목록 조회를 담당한다."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def create_account(
        self,
        *,
        workspace_id: str,
        name: str,
        description: str | None = None,
        created_by_user_id: str | None = None,
    ) -> AccountContext:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("회사 이름은 비워둘 수 없습니다.")
        account = AccountContext.create(
            workspace_id=workspace_id,
            name=normalized_name,
            description=description,
            created_by_user_id=created_by_user_id,
        )
        return self._repository.create_account(account)

    def list_accounts(self, *, workspace_id: str, limit: int = 100) -> list[AccountContext]:
        return self._repository.list_accounts(workspace_id=workspace_id, limit=limit)

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
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("상대방 이름은 비워둘 수 없습니다.")
        if account_id is not None:
            self.require_account(workspace_id=workspace_id, account_id=account_id)
        contact = ContactContext.create(
            workspace_id=workspace_id,
            account_id=account_id,
            name=normalized_name,
            email=email,
            job_title=job_title,
            department=department,
            notes=notes,
            created_by_user_id=created_by_user_id,
        )
        return self._repository.create_contact(contact)

    def list_contacts(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[ContactContext]:
        if account_id is not None:
            self.require_account(workspace_id=workspace_id, account_id=account_id)
        return self._repository.list_contacts(
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
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("스레드 제목은 비워둘 수 없습니다.")

        resolved_account_id = account_id
        if contact_id is not None:
            contact = self.require_contact(workspace_id=workspace_id, contact_id=contact_id)
            if resolved_account_id is None:
                resolved_account_id = contact.account_id
            elif contact.account_id and contact.account_id != resolved_account_id:
                raise ValueError("상대방과 회사 연결 정보가 서로 맞지 않습니다.")
        if resolved_account_id is not None:
            self.require_account(workspace_id=workspace_id, account_id=resolved_account_id)

        thread = ContextThread.create(
            workspace_id=workspace_id,
            title=normalized_title,
            account_id=resolved_account_id,
            contact_id=contact_id,
            summary=summary,
            created_by_user_id=created_by_user_id,
        )
        return self._repository.create_context_thread(thread)

    def list_context_threads(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        limit: int = 100,
    ) -> list[ContextThread]:
        if account_id is not None:
            self.require_account(workspace_id=workspace_id, account_id=account_id)
        if contact_id is not None:
            self.require_contact(workspace_id=workspace_id, contact_id=contact_id)
        return self._repository.list_context_threads(
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            limit=limit,
        )

    def require_account(self, *, workspace_id: str, account_id: str) -> AccountContext:
        account = self._repository.get_account(account_id=account_id, workspace_id=workspace_id)
        if account is None:
            raise ValueError(f"회사 맥락을 찾지 못했습니다: {account_id}")
        return account

    def require_contact(self, *, workspace_id: str, contact_id: str) -> ContactContext:
        contact = self._repository.get_contact(contact_id=contact_id, workspace_id=workspace_id)
        if contact is None:
            raise ValueError(f"상대방 맥락을 찾지 못했습니다: {contact_id}")
        return contact

    def require_context_thread(self, *, workspace_id: str, thread_id: str) -> ContextThread:
        thread = self._repository.get_context_thread(thread_id=thread_id, workspace_id=workspace_id)
        if thread is None:
            raise ValueError(f"스레드 맥락을 찾지 못했습니다: {thread_id}")
        return thread
