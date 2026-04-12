"""세션 라우트 공통 유틸리티."""

from __future__ import annotations

from server.app.api.http.dependencies import (
    get_participation_query_service,
)
from server.app.api.http.schemas.meeting_session import SessionResponse
from server.app.api.http.schemas.participation import (
    SessionParticipationSummaryResponse,
)
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.models.auth_session import AuthenticatedSession


def resolve_workspace_id(auth_context: AuthenticatedSession | None) -> str:
    """인증 컨텍스트에서 workspace id를 계산한다."""

    if auth_context is None:
        return DEFAULT_WORKSPACE_ID
    return auth_context.user.workspace_id or DEFAULT_WORKSPACE_ID


def to_session_response(session, *, workspace_id: str) -> SessionResponse:
    """도메인 세션을 API 응답 모델로 변환한다."""

    participation = get_participation_query_service().build_session_participation(
        session=session,
        workspace_id=workspace_id,
    )
    return SessionResponse(
        id=session.id,
        title=session.title,
        mode=session.mode.value,
        status=session.status.value,
        started_at=session.started_at,
        created_by_user_id=session.created_by_user_id,
        account_id=session.account_id,
        contact_id=session.contact_id,
        context_thread_id=session.context_thread_id,
        ended_at=session.ended_at,
        primary_input_source=session.primary_input_source,
        actual_active_sources=list(session.actual_active_sources),
        participants=list(session.participants),
        participant_summary=SessionParticipationSummaryResponse(
            total_count=participation.summary.total_count,
            linked_count=participation.summary.linked_count,
            unmatched_count=participation.summary.unmatched_count,
            ambiguous_count=participation.summary.ambiguous_count,
            unresolved_count=participation.summary.unresolved_count,
            pending_followup_count=participation.summary.pending_followup_count,
            resolved_followup_count=participation.summary.resolved_followup_count,
        ),
    )
