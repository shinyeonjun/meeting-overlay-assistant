"""PostgreSQL 미팅 컨텍스트 저장소."""

from __future__ import annotations

from server.app.domain.context import AccountContext, ContactContext, ContextThread
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories.context.context_helpers import (
    fetch_account_row,
    fetch_account_rows,
    fetch_contact_row,
    fetch_contact_rows,
    fetch_contacts_by_names_rows,
    fetch_context_thread_row,
    fetch_context_thread_rows,
    insert_account,
    insert_contact,
    insert_context_thread,
    to_account,
    to_contact,
    to_context_thread,
)


class PostgreSQLMeetingContextRepository:
    """회사, 담당자, 스레드 맥락을 PostgreSQL에 저장한다."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def create_account(self, account: AccountContext) -> AccountContext:
        """계정 컨텍스트를 저장한다."""

        with self._database.transaction() as connection:
            insert_account(connection, account)
        return account

    def list_accounts(self, *, workspace_id: str, limit: int = 100) -> list[AccountContext]:
        """활성 계정 목록을 조회한다."""

        with self._database.transaction() as connection:
            rows = fetch_account_rows(connection, workspace_id=workspace_id, limit=limit)
        return [self._to_account(row) for row in rows]

    def get_account(self, *, account_id: str, workspace_id: str) -> AccountContext | None:
        """계정 한 건을 조회한다."""

        with self._database.transaction() as connection:
            row = fetch_account_row(connection, account_id=account_id, workspace_id=workspace_id)
        return self._to_account(row) if row is not None else None

    def create_contact(self, contact: ContactContext) -> ContactContext:
        """연락처 컨텍스트를 저장한다."""

        with self._database.transaction() as connection:
            insert_contact(connection, contact)
        return contact

    def list_contacts(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[ContactContext]:
        """활성 연락처 목록을 조회한다."""

        with self._database.transaction() as connection:
            rows = fetch_contact_rows(
                connection,
                workspace_id=workspace_id,
                account_id=account_id,
                limit=limit,
            )
        return [self._to_contact(row) for row in rows]

    def get_contact(self, *, contact_id: str, workspace_id: str) -> ContactContext | None:
        """연락처 한 건을 조회한다."""

        with self._database.transaction() as connection:
            row = fetch_contact_row(connection, contact_id=contact_id, workspace_id=workspace_id)
        return self._to_contact(row) if row is not None else None

    def list_contacts_by_names(
        self,
        *,
        workspace_id: str,
        names: list[str] | tuple[str, ...],
        account_id: str | None = None,
    ) -> list[ContactContext]:
        """이름 목록과 일치하는 연락처를 조회한다."""

        normalized_names: list[str] = []
        seen: set[str] = set()
        for value in names:
            stripped = value.strip()
            if not stripped or stripped in seen:
                continue
            normalized_names.append(stripped)
            seen.add(stripped)

        if not normalized_names:
            return []

        with self._database.transaction() as connection:
            rows = fetch_contacts_by_names_rows(
                connection,
                workspace_id=workspace_id,
                names=normalized_names,
                account_id=account_id,
            )
        return [self._to_contact(row) for row in rows]

    def create_context_thread(self, thread: ContextThread) -> ContextThread:
        """컨텍스트 스레드를 저장한다."""

        with self._database.transaction() as connection:
            insert_context_thread(connection, thread)
        return thread

    def list_context_threads(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        limit: int = 100,
    ) -> list[ContextThread]:
        """활성 컨텍스트 스레드 목록을 조회한다."""

        with self._database.transaction() as connection:
            rows = fetch_context_thread_rows(
                connection,
                workspace_id=workspace_id,
                account_id=account_id,
                contact_id=contact_id,
                limit=limit,
            )
        return [self._to_context_thread(row) for row in rows]

    def get_context_thread(self, *, thread_id: str, workspace_id: str) -> ContextThread | None:
        """컨텍스트 스레드 한 건을 조회한다."""

        with self._database.transaction() as connection:
            row = fetch_context_thread_row(
                connection,
                thread_id=thread_id,
                workspace_id=workspace_id,
            )
        return self._to_context_thread(row) if row is not None else None

    @staticmethod
    def _to_account(row) -> AccountContext:
        """기존 내부 API 호환용 wrapper."""

        return to_account(row)

    @staticmethod
    def _to_contact(row) -> ContactContext:
        """기존 내부 API 호환용 wrapper."""

        return to_contact(row)

    @staticmethod
    def _to_context_thread(row) -> ContextThread:
        """기존 내부 API 호환용 wrapper."""

        return to_context_thread(row)
