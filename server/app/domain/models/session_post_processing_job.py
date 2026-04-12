"""세션 후처리 job 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_after_seconds_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=max(seconds, 1))).isoformat()


@dataclass(frozen=True)
class SessionPostProcessingJob:
    """회의 종료 후 canonical 데이터 생성을 담당하는 job 상태."""

    id: str
    session_id: str
    status: str
    recording_artifact_id: str | None
    recording_path: str | None
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
        recording_artifact_id: str | None,
        recording_path: str | None,
        requested_by_user_id: str | None = None,
    ) -> "SessionPostProcessingJob":
        """새 pending 후처리 job을 만든다."""

        return cls(
            id=f"post-job-{uuid4().hex}",
            session_id=session_id,
            status="pending",
            recording_artifact_id=recording_artifact_id,
            recording_path=recording_path,
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
    ) -> "SessionPostProcessingJob":
        """job을 processing 상태로 전이한다."""

        return SessionPostProcessingJob(
            id=self.id,
            session_id=self.session_id,
            status="processing",
            recording_artifact_id=self.recording_artifact_id,
            recording_path=self.recording_path,
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=claimed_by_worker_id,
            lease_expires_at=lease_expires_at,
            attempt_count=self.attempt_count + 1,
            created_at=self.created_at,
            started_at=started_at or _utc_now_iso(),
            completed_at=None,
        )

    def mark_completed(self) -> "SessionPostProcessingJob":
        """job을 completed 상태로 전이한다."""

        return SessionPostProcessingJob(
            id=self.id,
            session_id=self.session_id,
            status="completed",
            recording_artifact_id=self.recording_artifact_id,
            recording_path=self.recording_path,
            error_message=None,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def mark_failed(self, error_message: str) -> "SessionPostProcessingJob":
        """job을 failed 상태로 전이한다."""

        return SessionPostProcessingJob(
            id=self.id,
            session_id=self.session_id,
            status="failed",
            recording_artifact_id=self.recording_artifact_id,
            recording_path=self.recording_path,
            error_message=error_message,
            requested_by_user_id=self.requested_by_user_id,
            claimed_by_worker_id=None,
            lease_expires_at=None,
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            started_at=self.started_at or _utc_now_iso(),
            completed_at=_utc_now_iso(),
        )

    def with_lease(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
    ) -> "SessionPostProcessingJob":
        """worker claim 정보를 포함한 processing 상태를 만든다."""

        return self.mark_processing(
            claimed_by_worker_id=worker_id,
            lease_expires_at=_utc_after_seconds_iso(lease_seconds),
        )
