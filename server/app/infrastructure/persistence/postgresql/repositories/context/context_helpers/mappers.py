"""미팅 컨텍스트 저장소 모델 매핑 helper."""

from __future__ import annotations

from server.app.domain.context import AccountContext, ContactContext, ContextThread


def to_account(row) -> AccountContext:
    """DB row를 AccountContext로 변환한다."""

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


def to_contact(row) -> ContactContext:
    """DB row를 ContactContext로 변환한다."""

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


def to_context_thread(row) -> ContextThread:
    """DB row를 ContextThread로 변환한다."""

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
