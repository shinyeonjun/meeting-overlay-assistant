"""HTTP 계층에서 공통 관련 workspace 구성을 담당한다."""
from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import resolve_scope_owner_id
from server.app.api.http.dependencies import (
    get_history_query_service,
    get_report_generation_job_service,
    get_report_service,
    get_session_service,
)
from server.app.api.http.routes.history.support import (
    resolve_workspace_id,
    to_carry_over_response,
    to_retrieval_brief_response,
    to_timeline_report_item,
    to_timeline_session_item,
)
from server.app.api.http.schemas.report import FinalReportStatusResponse
from server.app.api.http.schemas.workspace import (
    WorkspaceOverviewResponse,
    WorkspaceOverviewSummaryResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

MAX_WORKSPACE_OVERVIEW_LIMIT = 20

router = APIRouter(
    prefix="/api/v1/workspace",
    tags=["workspace"],
    dependencies=[Depends(require_authenticated_session)],
)


def _build_report_status_map(sessions: list[object]) -> dict[str, FinalReportStatusResponse]:
    report_job_service = get_report_generation_job_service()
    status_map = report_job_service.build_final_statuses(
        {session.id: session for session in sessions}
    )
    return {
        session_id: FinalReportStatusResponse(
            session_id=status.session_id,
            status=status.status,
            pipeline_stage=status.pipeline_stage,
            report_count=status.report_count,
            post_processing_status=status.post_processing_status,
            post_processing_error_message=status.post_processing_error_message,
            note_correction_job_status=status.note_correction_job_status,
            note_correction_job_error_message=status.note_correction_job_error_message,
            latest_report_id=status.latest_report_id,
            latest_report_type=status.latest_report_type,
            latest_generated_at=status.latest_generated_at,
            latest_file_artifact_id=status.latest_file_artifact_id,
            latest_file_path=status.latest_file_path,
            warning_reason=status.warning_reason,
            latest_job_status=status.latest_job_status,
            latest_job_error_message=status.latest_job_error_message,
        )
        for session_id, status in status_map.items()
    }


@router.get("/overview", response_model=WorkspaceOverviewResponse)
def get_workspace_overview(
    scope: str = "mine",
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    limit: int = 8,
    include_reports: bool = True,
    include_carry_over: bool = True,
    include_retrieval_brief: bool = True,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> WorkspaceOverviewResponse:
    """web workspace 첫 화면에서 바로 쓰는 집계 응답을 반환한다."""

    workspace_id = resolve_workspace_id(auth_context)
    owner_filter = resolve_scope_owner_id(scope, auth_context)
    normalized_limit = max(1, min(limit, MAX_WORKSPACE_OVERVIEW_LIMIT))

    try:
        snapshot = get_history_query_service().get_timeline(
            workspace_id=workspace_id,
            owner_filter=owner_filter,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=normalized_limit,
            include_reports=include_reports,
            include_carry_over=include_carry_over,
            include_retrieval_brief=include_retrieval_brief,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    sessions_by_id = {item.id: item for item in snapshot.sessions}
    report_service = get_report_service()
    report_statuses = _build_report_status_map(list(snapshot.sessions))
    return WorkspaceOverviewResponse(
        workspace_id=workspace_id,
        scope=scope,
        account_id=snapshot.account_id,
        contact_id=snapshot.contact_id,
        context_thread_id=snapshot.context_thread_id,
        summary=WorkspaceOverviewSummaryResponse(
            active_session_count=get_session_service().count_running_sessions_filtered(
                created_by_user_id=owner_filter,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
            ),
            loaded_session_count=len(snapshot.sessions),
            report_count=report_service.count_recent_reports(
                generated_by_user_id=owner_filter,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
            ),
        ),
        sessions=[to_timeline_session_item(item) for item in snapshot.sessions],
        report_statuses=report_statuses,
        reports=[to_timeline_report_item(item) for item in snapshot.reports],
        carry_over=to_carry_over_response(snapshot.carry_over, sessions_by_id=sessions_by_id),
        retrieval_brief=to_retrieval_brief_response(snapshot.retrieval_brief),
    )
