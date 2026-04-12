"""회사/거래처 맥락 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AccountContext:
    """회사/거래처 단위 맥락."""

    id: str
    workspace_id: str
    name: str
    description: str | None
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
        description: str | None = None,
        created_by_user_id: str | None = None,
    ) -> "AccountContext":
        """회사/거래처 맥락을 생성한다."""

        now = _utc_now_iso()
        return cls(
            id=f"account-{uuid4().hex}",
            workspace_id=workspace_id,
            name=name.strip(),
            description=description.strip() if description else None,
            status="active",
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
        )
