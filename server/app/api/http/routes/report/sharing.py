"""회의록 공유 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.routes.report.support import (
    require_auth_context,
    to_latest_report_response,
    to_report_share_inbox_item_response,
    to_report_share_response,
)
from server.app.api.http.schemas.report import (
    LatestReportResponse,
    ReportShareCreateRequest,
    ReportShareInboxListResponse,
    ReportShareListResponse,
    ReportShareResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.services.reports.sharing.report_share_service import (
    DuplicateReportShareError,
    InvalidReportShareTargetError,
    ShareRecipientNotFoundError,
)

router = APIRouter()


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


@router.get("/shared-with-me", response_model=ReportShareInboxListResponse)
def list_shared_with_me_reports(
    limit: int = 20,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportShareInboxListResponse:
    """현재 사용자에게 공유된 회의록 목록을 조회한다."""

    current_user = require_auth_context(auth_context)
    shares = _reports_facade().get_report_share_service().list_received_shares(
        shared_with_user_id=current_user.user.id,
        limit=max(1, min(limit, 100)),
    )
    return ReportShareInboxListResponse(
        items=[to_report_share_inbox_item_response(item) for item in shares]
    )


@router.get("/shared-with-me/{report_id}", response_model=LatestReportResponse)
def get_shared_report_by_id(
    report_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> LatestReportResponse:
    """공유받은 회의록 본문을 조회한다."""

    current_user = require_auth_context(auth_context)
    report_share_service = _reports_facade().get_report_share_service()
    report_service = _reports_facade().get_report_service()
    share = report_share_service.get_share_for_recipient(
        report_id=report_id,
        shared_with_user_id=current_user.user.id,
    )
    if share is None:
        raise HTTPException(status_code=404, detail="공유받은 회의록을 찾을 수 없습니다.")

    report = report_service.get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="회의록을 찾을 수 없습니다.")

    return to_latest_report_response(
        report,
        content=report_service.read_report_content(report),
    )


@router.get("/{session_id}/{report_id}/shares", response_model=ReportShareListResponse)
def list_report_shares(
    session_id: str,
    report_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportShareListResponse:
    """회의록 공유 목록을 조회한다."""

    require_auth_context(auth_context)
    get_accessible_session_or_raise(session_id, auth_context)
    _reports_facade()._get_report_or_404(session_id=session_id, report_id=report_id)
    shares = _reports_facade().get_report_share_service().list_shares(report_id)
    return ReportShareListResponse(items=[to_report_share_response(item) for item in shares])


@router.post(
    "/{session_id}/{report_id}/shares",
    response_model=ReportShareResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report_share(
    session_id: str,
    report_id: str,
    request: ReportShareCreateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportShareResponse:
    """회의록을 다른 사용자에게 공유한다."""

    current_user = require_auth_context(auth_context)
    get_accessible_session_or_raise(session_id, current_user)
    report = _reports_facade()._get_report_or_404(session_id=session_id, report_id=report_id)

    try:
        share = _reports_facade().get_report_share_service().create_share(
            report=report,
            shared_by_user=current_user.user,
            shared_with_login_id=request.shared_with_login_id,
            note=request.note,
        )
    except ShareRecipientNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidReportShareTargetError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except DuplicateReportShareError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return to_report_share_response(share)
