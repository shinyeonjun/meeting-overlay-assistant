"""사용자 엔티티."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from server.app.core.identifiers import generate_uuid_str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class UserAccount:
    """사내용 사용자 계정 엔티티."""

    id: str
    login_id: str
    display_name: str
    job_title: str | None
    department: str | None
    status: str
    created_at: str
    updated_at: str
    workspace_id: str | None = None
    workspace_name: str | None = None
    workspace_slug: str | None = None
    workspace_role: str | None = None
    workspace_status: str | None = None

    @classmethod
    def create(
        cls,
        *,
        login_id: str,
        display_name: str,
        job_title: str | None = None,
        department: str | None = None,
        workspace_role: str = "member",
        status: str = "active",
    ) -> "UserAccount":
        """새 사용자 계정을 생성한다."""

        now = _utc_now_iso()
        return cls(
            id=generate_uuid_str(),
            login_id=login_id,
            display_name=display_name,
            job_title=job_title,
            department=department,
            status=status,
            created_at=now,
            updated_at=now,
            workspace_role=workspace_role,
        )
