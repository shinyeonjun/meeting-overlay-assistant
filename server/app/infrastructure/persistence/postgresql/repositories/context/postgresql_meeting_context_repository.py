"""PostgreSQL 회의 맥락 저장소."""

from __future__ import annotations

from server.app.domain.context import AccountContext, ContactContext, ContextThread
from server.app.infrastructure.persistence.postgresql.database import PostgreSQLDatabase


class PostgreSQLMeetingContextRepository:
    """회사/상대방/스레드 맥락을 PostgreSQL에 저장한다."""

    def __init__(self, database: PostgreSQLDatabase) -> None:
        self._database = database

    def create_account(self, account: AccountContext) -> AccountContext:
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO accounts (
                    id, workspace_id, name, description, status,
                    created_by_user_id, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    account.id,
                    account.workspace_id,
                    account.name,
                    account.description,
                    account.status,
                    account.created_by_user_id,
                    account.created_at,
                    account.updated_at,
                ),
            )
        return account

    def list_accounts(self, *, workspace_id: str, limit: int = 100) -> list[AccountContext]:
        with self._database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM accounts
                WHERE workspace_id = %s AND status = 'active'
                ORDER BY LOWER(name) ASC, created_at DESC
                LIMIT %s
                """,
                (workspace_id, limit),
            ).fetchall()
        return [self._to_account(row) for row in rows]

    def get_account(self, *, account_id: str, workspace_id: str) -> AccountContext | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM accounts
                WHERE id = %s AND workspace_id = %s
                """,
                (account_id, workspace_id),
            ).fetchone()
        return self._to_account(row) if row is not None else None

    def create_contact(self, contact: ContactContext) -> ContactContext:
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO contacts (
                    id, workspace_id, account_id, name, email, job_title, department,
                    notes, status, created_by_user_id, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    contact.id,
                    contact.workspace_id,
                    contact.account_id,
                    contact.name,
                    contact.email,
                    contact.job_title,
                    contact.department,
                    contact.notes,
                    contact.status,
                    contact.created_by_user_id,
                    contact.created_at,
                    contact.updated_at,
                ),
            )
        return contact

    def list_contacts(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[ContactContext]:
        query = """
            SELECT *
            FROM contacts
            WHERE workspace_id = %s AND status = 'active'
        """
        params: list[object] = [workspace_id]
        if account_id is not None:
            query += " AND account_id = %s"
            params.append(account_id)
        query += " ORDER BY LOWER(name) ASC, created_at DESC LIMIT %s"
        params.append(limit)

        with self._database.transaction() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._to_contact(row) for row in rows]

    def get_contact(self, *, contact_id: str, workspace_id: str) -> ContactContext | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM contacts
                WHERE id = %s AND workspace_id = %s
                """,
                (contact_id, workspace_id),
            ).fetchone()
        return self._to_contact(row) if row is not None else None

    def list_contacts_by_names(
        self,
        *,
        workspace_id: str,
        names: list[str] | tuple[str, ...],
        account_id: str | None = None,
    ) -> list[ContactContext]:
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

        query = """
            SELECT *
            FROM contacts
            WHERE workspace_id = %s
              AND status = 'active'
              AND name = ANY(%s)
        """
        params: list[object] = [workspace_id, normalized_names]
        if account_id is not None:
            query += " AND account_id = %s"
            params.append(account_id)
        query += " ORDER BY LOWER(name) ASC, created_at DESC"

        with self._database.transaction() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._to_contact(row) for row in rows]

    def create_context_thread(self, thread: ContextThread) -> ContextThread:
        with self._database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO context_threads (
                    id, workspace_id, account_id, contact_id, title, summary,
                    status, created_by_user_id, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    thread.id,
                    thread.workspace_id,
                    thread.account_id,
                    thread.contact_id,
                    thread.title,
                    thread.summary,
                    thread.status,
                    thread.created_by_user_id,
                    thread.created_at,
                    thread.updated_at,
                ),
            )
        return thread

    def list_context_threads(
        self,
        *,
        workspace_id: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        limit: int = 100,
    ) -> list[ContextThread]:
        query = """
            SELECT *
            FROM context_threads
            WHERE workspace_id = %s AND status = 'active'
        """
        params: list[object] = [workspace_id]
        if account_id is not None:
            query += " AND account_id = %s"
            params.append(account_id)
        if contact_id is not None:
            query += " AND contact_id = %s"
            params.append(contact_id)
        query += " ORDER BY updated_at DESC, created_at DESC LIMIT %s"
        params.append(limit)

        with self._database.transaction() as connection:
            rows = connection.execute(query, tuple(params)).fetchall()
        return [self._to_context_thread(row) for row in rows]

    def get_context_thread(self, *, thread_id: str, workspace_id: str) -> ContextThread | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM context_threads
                WHERE id = %s AND workspace_id = %s
                """,
                (thread_id, workspace_id),
            ).fetchone()
        return self._to_context_thread(row) if row is not None else None

    @staticmethod
    def _to_account(row) -> AccountContext:
        return AccountContext(
            id=row["id"],
            workspace_id=row["workspace_id"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            created_by_user_id=row["created_by_user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _to_contact(row) -> ContactContext:
        return ContactContext(
            id=row["id"],
            workspace_id=row["workspace_id"],
            account_id=row["account_id"],
            name=row["name"],
            email=row["email"],
            job_title=row["job_title"],
            department=row["department"],
            notes=row["notes"],
            status=row["status"],
            created_by_user_id=row["created_by_user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _to_context_thread(row) -> ContextThread:
        return ContextThread(
            id=row["id"],
            workspace_id=row["workspace_id"],
            account_id=row["account_id"],
            contact_id=row["contact_id"],
            title=row["title"],
            summary=row["summary"],
            status=row["status"],
            created_by_user_id=row["created_by_user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
