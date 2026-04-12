"""history 조회 라우트."""

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import resolve_scope_owner_id
from server.app.api.http.dependencies import get_history_query_service
from server.app.api.http.routes.history.support import (
    resolve_workspace_id,
    to_carry_over_response,
    to_retrieval_brief_response,
    to_timeline_report_item,
    to_timeline_session_item,
)
from server.app.api.http.schemas.history import HistoryTimelineResponse
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

MAX_TIMELINE_LIMIT = 20

router = APIRouter()


@router.get("/timeline", response_model=HistoryTimelineResponse)
def get_history_timeline(
    scope: str = "mine",
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    limit: int = 8,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> HistoryTimelineResponse:
    """선택한 맥락의 최근 세션/리포트/이어보기 브리프를 조회한다."""

    workspace_id = resolve_workspace_id(auth_context)
    owner_filter = resolve_scope_owner_id(scope, auth_context)
    normalized_limit = max(1, min(limit, MAX_TIMELINE_LIMIT))

    try:
        snapshot = get_history_query_service().get_timeline(
            workspace_id=workspace_id,
            owner_filter=owner_filter,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=normalized_limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    sessions_by_id = {item.id: item for item in snapshot.sessions}
    return HistoryTimelineResponse(
        account_id=snapshot.account_id,
        contact_id=snapshot.contact_id,
        context_thread_id=snapshot.context_thread_id,
        session_count=len(snapshot.sessions),
        report_count=len(snapshot.reports),
        sessions=[to_timeline_session_item(item) for item in snapshot.sessions],
        reports=[to_timeline_report_item(item) for item in snapshot.reports],
        carry_over=to_carry_over_response(snapshot.carry_over, sessions_by_id=sessions_by_id),
        retrieval_brief=to_retrieval_brief_response(snapshot.retrieval_brief),
    )
