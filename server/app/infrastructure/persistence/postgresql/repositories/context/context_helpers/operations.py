"""미팅 컨텍스트 저장소 SQL 실행 helper."""

from __future__ import annotations

from server.app.domain.context import AccountContext, ContactContext, ContextThread


def insert_account(connection, account: AccountContext) -> None:
    """계정 컨텍스트를 저장한다."""

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


def fetch_account_rows(connection, *, workspace_id: str, limit: int):
    """활성 계정 목록 row를 조회한다."""

    return connection.execute(
        """
        SELECT *
        FROM accounts
        WHERE workspace_id = %s AND status = 'active'
        ORDER BY LOWER(name) ASC, created_at DESC
        LIMIT %s
        """,
        (workspace_id, limit),
    ).fetchall()


def fetch_account_row(connection, *, account_id: str, workspace_id: str):
    """계정 한 건 row를 조회한다."""

    return connection.execute(
        """
        SELECT *
        FROM accounts
        WHERE id = %s AND workspace_id = %s
        """,
        (account_id, workspace_id),
    ).fetchone()


def insert_contact(connection, contact: ContactContext) -> None:
    """연락처 컨텍스트를 저장한다."""

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


def fetch_contact_rows(
    connection,
    *,
    workspace_id: str,
    account_id: str | None = None,
    limit: int,
):
    """활성 연락처 목록 row를 조회한다."""

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
    return connection.execute(query, tuple(params)).fetchall()


def fetch_contact_row(connection, *, contact_id: str, workspace_id: str):
    """연락처 한 건 row를 조회한다."""

    return connection.execute(
        """
        SELECT *
        FROM contacts
        WHERE id = %s AND workspace_id = %s
        """,
        (contact_id, workspace_id),
    ).fetchone()


def fetch_contacts_by_names_rows(
    connection,
    *,
    workspace_id: str,
    names: list[str],
    account_id: str | None = None,
):
    """이름 기준 연락처 row를 조회한다."""

    query = """
        SELECT *
        FROM contacts
        WHERE workspace_id = %s
          AND status = 'active'
          AND name = ANY(%s)
    """
    params: list[object] = [workspace_id, names]
    if account_id is not None:
        query += " AND account_id = %s"
        params.append(account_id)
    query += " ORDER BY LOWER(name) ASC, created_at DESC"
    return connection.execute(query, tuple(params)).fetchall()


def insert_context_thread(connection, thread: ContextThread) -> None:
    """컨텍스트 스레드를 저장한다."""

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


def fetch_context_thread_rows(
    connection,
    *,
    workspace_id: str,
    account_id: str | None = None,
    contact_id: str | None = None,
    limit: int,
):
    """활성 컨텍스트 스레드 row를 조회한다."""

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
    return connection.execute(query, tuple(params)).fetchall()


def fetch_context_thread_row(connection, *, thread_id: str, workspace_id: str):
    """컨텍스트 스레드 한 건 row를 조회한다."""

    return connection.execute(
        """
        SELECT *
        FROM context_threads
        WHERE id = %s AND workspace_id = %s
        """,
        (thread_id, workspace_id),
    ).fetchone()
