"""상대방 맥락 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ContactContext:
    """회의 상대방 인물 맥락."""

    id: str
    workspace_id: str
    account_id: str | None
    name: str
    email: str | None
    job_title: str | None
    department: str | None
    notes: str | None
    status: str
    created_by_user_id: str | None
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        *,
        workspace_id: str,
        name: str,
        account_id: str | None = None,
        email: str | None = None,
        job_title: str | None = None,
        department: str | None = None,
        notes: str | None = None,
        created_by_user_id: str | None = None,
    ) -> "ContactContext":
        """회의 상대방 맥락을 생성한다."""

        now = _utc_now_iso()
        return cls(
            id=f"contact-{uuid4().hex}",
            workspace_id=workspace_id,
            account_id=account_id,
            name=name.strip(),
            email=email.strip().lower() if email else None,
            job_title=job_title.strip() if job_title else None,
            department=department.strip() if department else None,
            notes=notes.strip() if notes else None,
            status="active",
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
