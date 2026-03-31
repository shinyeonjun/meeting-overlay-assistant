"""리포트 공유 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class ReportShare:
    """내부 사용자 간 리포트 공유 레코드."""

    id: str
    report_id: str
    shared_by_user_id: str
    shared_with_user_id: str
    permission: str
    note: str | None
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        report_id: str,
        shared_by_user_id: str,
        shared_with_user_id: str,
        permission: str = "view",
        note: str | None = None,
    ) -> "ReportShare":
        """새 리포트 공유 레코드를 생성한다."""

        return cls(
            id=f"report-share-{uuid4().hex}",
            report_id=report_id,
            shared_by_user_id=shared_by_user_id,
            shared_with_user_id=shared_with_user_id,
            permission=permission,
            note=note,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class ReportShareView:
    """공유 상세 조회용 리포트 공유 모델."""

    id: str
    report_id: str
    shared_by_user_id: str
    shared_by_login_id: str
    shared_by_display_name: str
    shared_with_user_id: str
    shared_with_login_id: str
    shared_with_display_name: str
    permission: str
    note: str | None
    created_at: str


@dataclass(frozen=True)
class ReceivedReportShareView:
    """공유받은 리포트 수신함 조회 모델."""

    share_id: str
    report_id: str
    session_id: str
    report_type: str
    version: int
    file_artifact_id: str | None
    file_path: str
    insight_source: str
    generated_by_user_id: str | None
    generated_at: str
    shared_by_user_id: str
    shared_by_login_id: str
    shared_by_display_name: str
    permission: str
    note: str | None
    shared_at: str
