"""참여자 후속 작업 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

from server.app.core.identifiers import generate_uuid_str


def utc_now_iso() -> str:
    """현재 UTC 시각을 ISO 문자열로 반환한다."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ParticipantFollowup:
    """세션 참여자의 후속 정리 작업을 표현한다."""

    id: str
    session_id: str
    participant_order: int
    participant_name: str
    resolution_status: str
    followup_status: str
    matched_contact_count: int
    contact_id: str | None = None
    account_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    resolved_at: str | None = None
    resolved_by_user_id: str | None = None

    @classmethod
    def create_pending(
        cls,
        *,
        session_id: str,
        participant_order: int,
        participant_name: str,
        resolution_status: str,
        matched_contact_count: int,
        contact_id: str | None = None,
        account_id: str | None = None,
    ) -> "ParticipantFollowup":
        """미해결 참여자 후속 작업을 생성한다."""

        now = utc_now_iso()
        return cls(
            id=generate_uuid_str(),
            session_id=session_id,
            participant_order=participant_order,
            participant_name=participant_name,
            resolution_status=resolution_status,
            followup_status="pending",
            matched_contact_count=matched_contact_count,
            contact_id=contact_id,
            account_id=account_id,
            created_at=now,
            updated_at=now,
        )

    def resolve(
        self,
        *,
        contact_id: str | None = None,
        resolved_by_user_id: str | None = None,
    ) -> "ParticipantFollowup":
        """후속 작업을 해결 상태로 전이한다."""

        now = utc_now_iso()
        return replace(
            self,
            contact_id=contact_id or self.contact_id,
            followup_status="resolved",
            updated_at=now,
            resolved_at=now,
            resolved_by_user_id=resolved_by_user_id,
        )

    def reopen(self) -> "ParticipantFollowup":
        """후속 작업을 다시 미해결 상태로 되돌린다."""

        now = utc_now_iso()
        return replace(
            self,
            followup_status="pending",
            updated_at=now,
            resolved_at=None,
            resolved_by_user_id=None,
        )
