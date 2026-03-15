"""이벤트 조회/수정/삭제 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import (
    get_event_lifecycle_service,
    get_event_management_service,
)
from server.app.api.http.routes.events.support import (
    raise_event_error,
    to_event_response,
)
from server.app.api.http.schemas.events.requests import EventUpdateRequest
from server.app.api.http.schemas.events.responses import EventItemResponse, EventListResponse
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.domain.shared.enums import EventState, EventType


router = APIRouter()


@router.get("/", response_model=EventListResponse)
def list_events(
    session_id: str,
    event_type: str | None = None,
    state: str | None = None,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> EventListResponse:
    """세션 이벤트 목록을 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    event_management_service = get_event_management_service()
    try:
        resolved_event_type = EventType(event_type) if event_type else None
        resolved_state = EventState(state) if state else None
        items = event_management_service.list_events(
            session_id,
            event_type=resolved_event_type,
            state=resolved_state,
        )
    except ValueError as error:
        raise_event_error(error)

    return EventListResponse(items=[to_event_response(item) for item in items])


@router.get("/{event_id}", response_model=EventItemResponse)
def get_event(
    session_id: str,
    event_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> EventItemResponse:
    """이벤트 단건을 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    event_management_service = get_event_management_service()
    try:
        event = event_management_service.get_event(session_id, event_id)
    except ValueError as error:
        raise_event_error(error)
    return to_event_response(event)


@router.patch("/{event_id}", response_model=EventItemResponse)
def update_event(
    session_id: str,
    event_id: str,
    request: EventUpdateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> EventItemResponse:
    """이벤트를 수동 수정한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    event_management_service = get_event_management_service()
    lifecycle_service = get_event_lifecycle_service()

    try:
        if request.state is not None:
            updated = lifecycle_service.transition_event(
                session_id,
                event_id,
                target_state=EventState(request.state),
                title=request.title,
                body=request.body,
                evidence_text=request.evidence_text,
                speaker_label=request.speaker_label,
            )
            if request.event_type is not None:
                updated = event_management_service.update_event(
                    session_id,
                    event_id,
                    event_type=EventType(request.event_type),
                )
        else:
            updated = event_management_service.update_event(
                session_id,
                event_id,
                event_type=EventType(request.event_type) if request.event_type else None,
                title=request.title,
                body=request.body,
                evidence_text=request.evidence_text,
                speaker_label=request.speaker_label,
            )
    except ValueError as error:
        raise_event_error(error)

    return to_event_response(updated)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    session_id: str,
    event_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> Response:
    """이벤트를 삭제한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    event_management_service = get_event_management_service()
    try:
        event_management_service.delete_event(session_id, event_id)
    except ValueError as error:
        raise_event_error(error)
    return Response(status_code=204)
