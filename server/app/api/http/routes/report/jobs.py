"""HTTP 계층에서 리포트 관련 jobs 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.schemas.report import ReportGenerationJobResponse
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


def _to_job_response(job) -> ReportGenerationJobResponse:
    return ReportGenerationJobResponse(
        id=job.id,
        session_id=job.session_id,
        status=job.status,
        recording_artifact_id=job.recording_artifact_id,
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


@router.post("/{session_id}/job", response_model=ReportGenerationJobResponse)
def enqueue_report_generation_job(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportGenerationJobResponse:
    """회의 종료 후 명시적으로 리포트 생성 job을 등록한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    if session.ended_at is None:
        raise HTTPException(
            status_code=409,
            detail="리포트 생성은 회의 종료 후에만 요청할 수 있습니다.",
        )

    process_report_jobs_inline = bool(
        getattr(request.app.state, "process_report_jobs_inline", False)
    )
    report_job_service = _reports_facade().get_report_job_service()
    job = report_job_service.enqueue_for_session(
        session_id=session_id,
        requested_by_user_id=auth_context.user.id if auth_context is not None else None,
        dispatch=not process_report_jobs_inline,
    )

    if process_report_jobs_inline and job.status == "pending":
        background_tasks.add_task(report_job_service.process_job, job.id)

    return _to_job_response(job)


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
    return _to_job_response(job)
