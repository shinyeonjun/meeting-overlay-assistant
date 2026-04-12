"""세션 생성에 사용할 검증 완료 맥락."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedMeetingContext:
    """세션에 연결 가능한 검증 완료 맥락."""

    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        """기존 호출자를 위한 dict 형태로 변환한다."""

        return {
            "account_id": self.account_id,
            "contact_id": self.contact_id,
            "context_thread_id": self.context_thread_id,
        }
