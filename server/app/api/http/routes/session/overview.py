"""세션 overview 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import get_session_overview_service
from server.app.api.http.routes.session.support import (
    resolve_workspace_id,
    to_session_response,
)
from server.app.api.http.schemas.meeting_session import (
    OverviewEventItemResponse,
    OverviewMetricsResponse,
    SessionOverviewResponse,
    WorkspaceSummaryActionItemResponse,
    WorkspaceSummaryEvidenceResponse,
    WorkspaceSummaryTopicResponse,
    WorkspaceSummaryResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


@router.get("/{session_id}/overview", response_model=SessionOverviewResponse)
def get_session_overview(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionOverviewResponse:
    """세션 overview를 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    overview_service = get_session_overview_service()
    try:
        overview = overview_service.build_overview(session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return SessionOverviewResponse(
        session=to_session_response(
            overview.session,
            workspace_id=resolve_workspace_id(auth_context),
        ),
        current_topic=overview.current_topic,
        questions=[
            OverviewEventItemResponse(
                id=item.id,
                title=item.title,
                state=item.state,
                speaker_label=item.speaker_label,
            )
            for item in overview.questions
        ],
        decisions=[
            OverviewEventItemResponse(
                id=item.id,
                title=item.title,
                state=item.state,
                speaker_label=item.speaker_label,
            )
            for item in overview.decisions
        ],
        action_items=[
            OverviewEventItemResponse(
                id=item.id,
                title=item.title,
                state=item.state,
                speaker_label=item.speaker_label,
            )
            for item in overview.action_items
        ],
        risks=[
            OverviewEventItemResponse(
                id=item.id,
                title=item.title,
                state=item.state,
                speaker_label=item.speaker_label,
            )
            for item in overview.risks
        ],
        workspace_summary=(
            WorkspaceSummaryResponse(
                headline=overview.workspace_summary.headline,
                summary=overview.workspace_summary.summary,
                topics=[
                    WorkspaceSummaryTopicResponse(
                        title=item.title,
                        summary=item.summary,
                        start_ms=item.start_ms,
                        end_ms=item.end_ms,
                    )
                    for item in overview.workspace_summary.topics
                ],
                decisions=overview.workspace_summary.decisions,
                next_actions=[
                    WorkspaceSummaryActionItemResponse(
                        title=item.title,
                        owner=item.owner,
                        due_date=item.due_date,
                    )
                    for item in overview.workspace_summary.next_actions
                ],
                open_questions=overview.workspace_summary.open_questions,
                changed_since_last_meeting=(
                    overview.workspace_summary.changed_since_last_meeting
                ),
                evidence=[
                    WorkspaceSummaryEvidenceResponse(
                        label=item.label,
                        start_ms=item.start_ms,
                        end_ms=item.end_ms,
                    )
                    for item in overview.workspace_summary.evidence
                ],
                model=overview.workspace_summary.model,
            )
            if overview.workspace_summary is not None
            else None
        ),
        metrics=OverviewMetricsResponse(
            recent_average_latency_ms=overview.recent_average_latency_ms,
            recent_utterance_count_by_source=overview.recent_utterance_count_by_source or {},
            insight_metrics=overview.insight_metrics or {},
        ),
    )
