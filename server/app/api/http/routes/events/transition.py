"""HTTP 계층에서 이벤트 관련 transition 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import get_event_lifecycle_service
from server.app.api.http.routes.events.support import (
    raise_event_error,
    to_event_response,
)
from server.app.api.http.schemas.events.requests import (
    BulkEventTransitionRequest,
    EventTransitionRequest,
)
from server.app.api.http.schemas.events.responses import (
    BulkEventTransitionResponse,
    EventItemResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.domain.shared.enums import EventState


router = APIRouter()


@router.post("/bulk-transition", response_model=BulkEventTransitionResponse)
def bulk_transition_events(
    session_id: str,
    request: BulkEventTransitionRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> BulkEventTransitionResponse:
    """여러 이벤트 상태를 한 번에 변경한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    lifecycle_service = get_event_lifecycle_service()
    try:
        items = lifecycle_service.bulk_transition_events(
            session_id,
            request.event_ids,
            target_state=EventState(request.target_state),
        )
    except ValueError as error:
        raise_event_error(error)

    return BulkEventTransitionResponse(
        updated_count=len(items),
        target_state=request.target_state,
        items=[to_event_response(item) for item in items],
    )


@router.post("/{event_id}/transition", response_model=EventItemResponse)
def transition_event(
    session_id: str,
    event_id: str,
    request: EventTransitionRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> EventItemResponse:
    """이벤트 상태를 검증된 규칙으로 전이한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    lifecycle_service = get_event_lifecycle_service()
    try:
        updated = lifecycle_service.transition_event(
            session_id,
            event_id,
            target_state=EventState(request.target_state),
            title=request.title,
            body=request.body,
            evidence_text=request.evidence_text,
            speaker_label=request.speaker_label,
        )
    except ValueError as error:
        raise_event_error(error)

    return to_event_response(updated)
