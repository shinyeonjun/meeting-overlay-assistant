"""리포트 job 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.schemas.report import ReportGenerationJobResponse
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


@router.get("/{session_id}/job", response_model=ReportGenerationJobResponse)
def get_latest_report_generation_job(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportGenerationJobResponse:
    """세션 기준 최신 리포트 생성 job 상태를 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    job = _reports_facade().get_report_job_service().get_latest_job(session_id)
    if job is None:
        raise HTTPException(status_code=404, detail="리포트 생성 job이 없습니다.")
    return ReportGenerationJobResponse(
        id=job.id,
        session_id=job.session_id,
        status=job.status,
        recording_path=job.recording_path,
        transcript_path=job.transcript_path,
        markdown_report_id=job.markdown_report_id,
        pdf_report_id=job.pdf_report_id,
        error_message=job.error_message,
        requested_by_user_id=job.requested_by_user_id,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
