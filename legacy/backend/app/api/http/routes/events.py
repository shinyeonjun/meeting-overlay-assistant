"""이벤트 관리 라우트."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from backend.app.api.http.dependencies import (
    get_event_lifecycle_service,
    get_event_management_service,
)
from backend.app.api.http.schemas.events import (
    BulkEventTransitionRequest,
    BulkEventTransitionResponse,
    EventItemResponse,
    EventListResponse,
    EventTransitionRequest,
    EventUpdateRequest,
)
from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.shared.enums import EventPriority, EventState, EventType


router = APIRouter(prefix="/api/v1/sessions/{session_id}/events", tags=["events"])


def _to_event_response(event: MeetingEvent) -> EventItemResponse:
    return EventItemResponse(
        id=event.id,
        session_id=event.session_id,
        event_type=event.event_type.value,
        title=event.title,
        body=event.body,
        evidence_text=event.evidence_text,
        speaker_label=event.speaker_label,
        state=event.state.value,
        priority=int(event.priority),
        assignee=event.assignee,
        due_date=event.due_date,
        topic_group=event.topic_group,
        source_utterance_id=event.source_utterance_id,
        source_screen_id=event.source_screen_id,
        created_at_ms=event.created_at_ms,
        updated_at_ms=event.updated_at_ms,
        input_source=event.input_source,
        insight_scope=event.insight_scope,
    )


def _raise_event_error(error: ValueError) -> None:
    detail = str(error)
    status_code = 404 if detail == "이벤트를 찾을 수 없습니다." else 400
    raise HTTPException(status_code=status_code, detail=detail) from error


@router.get("", response_model=EventListResponse)
def list_events(
    session_id: str,
    event_type: str | None = None,
    state: str | None = None,
) -> EventListResponse:
    """세션 이벤트 목록을 조회한다."""

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
        raise HTTPException(status_code=400, detail=str(error)) from error

    return EventListResponse(items=[_to_event_response(item) for item in items])


@router.post("/bulk-transition", response_model=BulkEventTransitionResponse)
def bulk_transition_events(
    session_id: str,
    request: BulkEventTransitionRequest,
) -> BulkEventTransitionResponse:
    """여러 이벤트 상태를 한 번에 변경한다."""

    lifecycle_service = get_event_lifecycle_service()
    try:
        items = lifecycle_service.bulk_transition_events(
            session_id,
            request.event_ids,
            target_state=EventState(request.target_state),
            assignee=request.assignee,
            due_date=request.due_date,
        )
    except ValueError as error:
        _raise_event_error(error)

    return BulkEventTransitionResponse(
        updated_count=len(items),
        target_state=request.target_state,
        items=[_to_event_response(item) for item in items],
    )


@router.get("/{event_id}", response_model=EventItemResponse)
def get_event(session_id: str, event_id: str) -> EventItemResponse:
    """이벤트 단건을 조회한다."""

    event_management_service = get_event_management_service()
    try:
        event = event_management_service.get_event(session_id, event_id)
    except ValueError as error:
        _raise_event_error(error)
    return _to_event_response(event)


@router.post("/{event_id}/transition", response_model=EventItemResponse)
def transition_event(
    session_id: str,
    event_id: str,
    request: EventTransitionRequest,
) -> EventItemResponse:
    """이벤트 상태를 검증된 규칙으로 전이한다."""

    lifecycle_service = get_event_lifecycle_service()
    try:
        updated = lifecycle_service.transition_event(
            session_id,
            event_id,
            target_state=EventState(request.target_state),
            title=request.title,
            body=request.body,
            assignee=request.assignee,
            due_date=request.due_date,
            evidence_text=request.evidence_text,
            speaker_label=request.speaker_label,
            topic_group=request.topic_group,
        )
    except ValueError as error:
        _raise_event_error(error)

    return _to_event_response(updated)


@router.patch("/{event_id}", response_model=EventItemResponse)
def update_event(
    session_id: str,
    event_id: str,
    request: EventUpdateRequest,
) -> EventItemResponse:
    """이벤트를 수동 보정한다."""

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
                assignee=request.assignee,
                due_date=request.due_date,
                evidence_text=request.evidence_text,
                speaker_label=request.speaker_label,
                topic_group=request.topic_group,
            )
            if request.event_type is not None or request.priority is not None:
                updated = event_management_service.update_event(
                    session_id,
                    event_id,
                    event_type=EventType(request.event_type) if request.event_type else None,
                    priority=EventPriority(request.priority) if request.priority is not None else None,
                )
        else:
            updated = event_management_service.update_event(
                session_id,
                event_id,
                event_type=EventType(request.event_type) if request.event_type else None,
                title=request.title,
                body=request.body,
                state=None,
                assignee=request.assignee,
                due_date=request.due_date,
                evidence_text=request.evidence_text,
                speaker_label=request.speaker_label,
                topic_group=request.topic_group,
                priority=EventPriority(request.priority) if request.priority is not None else None,
            )
    except ValueError as error:
        _raise_event_error(error)

    return _to_event_response(updated)


@router.delete("/{event_id}", status_code=204)
def delete_event(session_id: str, event_id: str) -> Response:
    """이벤트를 삭제한다."""

    event_management_service = get_event_management_service()
    try:
        event_management_service.delete_event(session_id, event_id)
    except ValueError as error:
        _raise_event_error(error)
    return Response(status_code=204)
