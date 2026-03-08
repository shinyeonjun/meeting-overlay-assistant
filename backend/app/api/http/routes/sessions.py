"""세션 라우터."""

from fastapi import APIRouter, HTTPException

from backend.app.api.http.dependencies import (
    get_session_finalization_service,
    get_session_overview_service,
    get_session_service,
)
from backend.app.api.http.schemas.overview import (
    OverviewEventItemResponse,
    OverviewMetricsResponse,
    SessionOverviewResponse,
)
from backend.app.api.http.schemas.session import SessionCreateRequest, SessionResponse
from backend.app.domain.shared.enums import AudioSource, SessionMode


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _to_session_response(session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        mode=session.mode.value,
        source=session.source.value,
        status=session.status.value,
        started_at=session.started_at,
        ended_at=session.ended_at,
        primary_input_source=session.primary_input_source,
        actual_active_sources=list(session.actual_active_sources),
    )


@router.post("", response_model=SessionResponse)
def create_session(request: SessionCreateRequest) -> SessionResponse:
    """새 세션을 생성한다."""

    session_service = get_session_service()
    try:
        session = session_service.start_session(
            title=request.title,
            mode=SessionMode(request.mode),
            source=AudioSource(request.source),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _to_session_response(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
def end_session(session_id: str) -> SessionResponse:
    """세션을 종료하고 최종 리포트를 생성한다."""

    finalization_service = get_session_finalization_service()
    try:
        session = finalization_service.finalize_session(session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return _to_session_response(session)


@router.get("/{session_id}/overview", response_model=SessionOverviewResponse)
def get_session_overview(session_id: str) -> SessionOverviewResponse:
    """세션 overview를 조회한다."""

    overview_service = get_session_overview_service()
    try:
        overview = overview_service.build_overview(session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return SessionOverviewResponse(
        session=_to_session_response(overview.session),
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
        metrics=OverviewMetricsResponse(
            recent_average_latency_ms=overview.recent_average_latency_ms,
            recent_utterance_count_by_source=overview.recent_utterance_count_by_source or {},
            insight_metrics=overview.insight_metrics or {},
        ),
    )
