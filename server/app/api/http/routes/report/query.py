"""리포트 조회 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import (
    get_accessible_session_or_raise,
    resolve_scope_owner_id,
)
from server.app.api.http.routes.report.support import (
    to_latest_report_response,
    to_report_item_response,
)
from server.app.api.http.schemas.report import (
    FinalReportStatusResponse,
    LatestReportResponse,
    ReportListResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


@router.get("/", response_model=ReportListResponse)
def list_recent_reports(
    scope: str = "mine",
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    limit: int = 20,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportListResponse:
    """최신 리포트 목록을 조회한다."""

    owner_filter = resolve_scope_owner_id(scope, auth_context)
    reports = _reports_facade().get_report_service().list_recent_reports(
        generated_by_user_id=owner_filter,
        account_id=account_id,
        contact_id=contact_id,
        context_thread_id=context_thread_id,
        limit=max(1, min(limit, 100)),
    )
    return ReportListResponse(items=[to_report_item_response(report) for report in reports])


@router.get("/{session_id}", response_model=ReportListResponse)
def list_reports(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportListResponse:
    """세션 리포트 목록을 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    reports = _reports_facade().get_report_service().list_reports(session_id)
    return ReportListResponse(items=[to_report_item_response(report) for report in reports])


@router.get("/{session_id}/latest", response_model=LatestReportResponse)
def get_latest_report(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> LatestReportResponse:
    """세션의 최신 리포트를 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report_service = _reports_facade().get_report_service()
    latest_report = report_service.get_latest_report(session_id)
    if latest_report is None:
        raise HTTPException(status_code=404, detail="리포트가 아직 생성되지 않았습니다.")
    return to_latest_report_response(
        latest_report,
        content=report_service.read_report_content(latest_report),
    )


@router.get("/{session_id}/final-status", response_model=FinalReportStatusResponse)
def get_final_report_status(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> FinalReportStatusResponse:
    """세션의 최종 문서 생성 상태를 조회한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    status_result = _reports_facade().get_report_job_service().build_final_status(
        session_id=session_id,
        session_ended=session.ended_at is not None,
    )
    return FinalReportStatusResponse(
        session_id=status_result.session_id,
        status=status_result.status,
        report_count=status_result.report_count,
        latest_report_id=status_result.latest_report_id,
        latest_report_type=status_result.latest_report_type,
        latest_generated_at=status_result.latest_generated_at,
        latest_file_artifact_id=status_result.latest_file_artifact_id,
        latest_file_path=status_result.latest_file_path,
        warning_reason=status_result.warning_reason,
        latest_job_status=status_result.latest_job_status,
        latest_job_error_message=status_result.latest_job_error_message,
    )


@router.get("/{session_id}/{report_id}", response_model=LatestReportResponse)
def get_report_by_id(
    session_id: str,
    report_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> LatestReportResponse:
    """리포트를 ID로 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report_service = _reports_facade().get_report_service()
    report = _reports_facade()._get_report_or_404(session_id=session_id, report_id=report_id)
    return to_latest_report_response(
        report,
        content=report_service.read_report_content(report),
    )
