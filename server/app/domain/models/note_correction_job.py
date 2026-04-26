"""노트 transcript 보정 job 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from server.app.core.identifiers import generate_uuid_str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_after_seconds_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(seconds, 1))).isoformat()


@dataclass(frozen=True)
class NoteCorrectionJob:
    """세션 transcript 보정 단계의 작업 상태를 보관한다."""

    id: str
    session_id: str
    source_version: int
    status: str
    error_message: str | None
    requested_by_user_id: str | None
    claimed_by_worker_id: str | None
    lease_expires_at: str | None
    attempt_count: int
    created_at: str
    started_at: str | None
    completed_at: str | None

    @classmethod
    def create_pending(
        cls,
        *,
        session_id: str,
        source_version: int,
        requested_by_user_id: str | None = None,
    ) -> "NoteCorrectionJob":
        """노트 보정 작업을 대기 상태로 만든다."""

        return cls(
            id=generate_uuid_str(),
            session_id=session_id,
            source_version=source_version,
            status="pending",
            error_message=None,
            requested_by_user_id=requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=0,
            created_at=_utc_now_iso(),
            started_at=None,
            completed_at=None,
        )

    def mark_processing(
        self,
        *,
        claimed_by_worker_id: str | None = None,
        lease_expires_at: str | None = None,
        started_at: str | None = None,
    ) -> "NoteCorrectionJob":
        """작업 상태를 처리 중으로 바꾼다."""

        return NoteCorrectionJob(
            id=self.id,
            session_id=self.session_id,
            source_version=self.source_version,
            status="processing",
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=claimed_by_worker_id,
            lease_expires_at=lease_expires_at,
            attempt_count=self.attempt_count + 1,
            created_at=self.created_at,
            started_at=started_at or _utc_now_iso(),
            completed_at=None,
        )

    def mark_completed(self) -> "NoteCorrectionJob":
        """작업 상태를 완료로 바꾼다."""

        return NoteCorrectionJob(
            id=self.id,
            session_id=self.session_id,
            source_version=self.source_version,
            status="completed",
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def mark_failed(self, error_message: str) -> "NoteCorrectionJob":
        """작업 상태를 실패로 바꾼다."""

        return NoteCorrectionJob(
            id=self.id,
            session_id=self.session_id,
            source_version=self.source_version,
            status="failed",
            error_message=error_message,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def with_lease(self, *, worker_id: str, lease_seconds: int) -> "NoteCorrectionJob":
        """worker claim 정보로 처리 중 상태를 만든다."""

        return self.mark_processing(
            claimed_by_worker_id=worker_id,
            lease_expires_at=_utc_after_seconds_iso(lease_seconds),
        )
