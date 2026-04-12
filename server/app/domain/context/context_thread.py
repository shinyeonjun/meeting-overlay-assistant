"""업무 흐름 스레드 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ContextThread:
    """같은 논의 흐름을 묶는 스레드."""

    id: str
    workspace_id: str
    account_id: str | None
    contact_id: str | None
    title: str
    summary: str | None
    status: str
    created_by_user_id: str | None
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        *,
        workspace_id: str,
        title: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        summary: str | None = None,
        created_by_user_id: str | None = None,
    ) -> "ContextThread":
        """회의 누적 스레드를 생성한다."""

        now = _utc_now_iso()
        return cls(
            id=f"context-thread-{uuid4().hex}",
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            title=title.strip(),
            summary=summary.strip() if summary else None,
            status="active",
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
