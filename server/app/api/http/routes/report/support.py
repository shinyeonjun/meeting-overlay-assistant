"""리포트 라우트 공통 지원 함수."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from server.app.api.http.schemas.report import (
    LatestReportResponse,
    ReportItemResponse,
    ReportShareInboxItemResponse,
    ReportShareResponse,
)
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.domain.models.report_share import ReceivedReportShareView, ReportShareView


def require_auth_context(
    auth_context: AuthenticatedSession | None,
) -> AuthenticatedSession:
    """인증 컨텍스트를 강제한다."""

    if auth_context is None:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    return auth_context


def to_report_item_response(report) -> ReportItemResponse:
    """리포트 메타데이터를 응답으로 변환한다."""

    return ReportItemResponse(
        id=report.id,
        session_id=report.session_id,
        report_type=report.report_type,
        version=report.version,
        file_artifact_id=report.file_artifact_id,
        file_path=report.file_path,
        insight_source=report.insight_source,
        generated_by_user_id=report.generated_by_user_id,
        generated_at=report.generated_at,
    )


def to_latest_report_response(report, *, content: str | None) -> LatestReportResponse:
    """리포트 상세를 응답으로 변환한다."""

    return LatestReportResponse(
        id=report.id,
        session_id=report.session_id,
        report_type=report.report_type,
        version=report.version,
        file_artifact_id=report.file_artifact_id,
        file_path=report.file_path,
        insight_source=report.insight_source,
        generated_by_user_id=report.generated_by_user_id,
        generated_at=report.generated_at,
        content=content,
    )


def to_report_share_response(share: ReportShareView) -> ReportShareResponse:
    """공유 모델을 응답으로 변환한다."""

    return ReportShareResponse(
        id=share.id,
        report_id=share.report_id,
        shared_by_user_id=share.shared_by_user_id,
        shared_by_login_id=share.shared_by_login_id,
        shared_by_display_name=share.shared_by_display_name,
        shared_with_user_id=share.shared_with_user_id,
        shared_with_login_id=share.shared_with_login_id,
        shared_with_display_name=share.shared_with_display_name,
        permission=share.permission,
        note=share.note,
        created_at=share.created_at,
    )


def to_report_share_inbox_item_response(
    share: ReceivedReportShareView,
) -> ReportShareInboxItemResponse:
    """공유받은 리포트 모델을 응답으로 변환한다."""

    file_reference = share.file_artifact_id or share.file_path
    return ReportShareInboxItemResponse(
        share_id=share.share_id,
        report_id=share.report_id,
        session_id=share.session_id,
        report_type=share.report_type,
        version=share.version,
        file_artifact_id=share.file_artifact_id,
        file_path=share.file_path,
        file_name=Path(file_reference).name,
        insight_source=share.insight_source,
        generated_by_user_id=share.generated_by_user_id,
        generated_at=share.generated_at,
        shared_by_user_id=share.shared_by_user_id,
        shared_by_login_id=share.shared_by_login_id,
        shared_by_display_name=share.shared_by_display_name,
        permission=share.permission,
        note=share.note,
        shared_at=share.shared_at,
    )
