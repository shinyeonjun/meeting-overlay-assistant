"""이벤트 상태 전이 규칙."""

from __future__ import annotations

from server.app.domain.shared.enums import EventState, EventType


_ALLOWED_TRANSITIONS: dict[EventType, dict[EventState, set[EventState]]] = {
    EventType.TOPIC: {
        EventState.ACTIVE: set(),
    },
    EventType.QUESTION: {
        EventState.OPEN: {EventState.ANSWERED, EventState.CLOSED},
        EventState.ANSWERED: {EventState.OPEN, EventState.CLOSED},
    },
    EventType.DECISION: {
        EventState.CONFIRMED: {EventState.UPDATED, EventState.CLOSED},
        EventState.UPDATED: {EventState.CONFIRMED, EventState.CLOSED},
    },
    EventType.ACTION_ITEM: {
        EventState.OPEN: {EventState.CLOSED},
        EventState.CLOSED: {EventState.OPEN},
    },
    EventType.RISK: {
        EventState.OPEN: {EventState.RESOLVED, EventState.CLOSED},
        EventState.RESOLVED: {EventState.OPEN, EventState.CLOSED},
    },
}


def can_transition_event(
    event_type: EventType,
    current_state: EventState,
    target_state: EventState,
) -> bool:
    """주어진 이벤트가 목표 상태로 전이 가능한지 반환한다."""

    if current_state == target_state:
        return True
    allowed = _ALLOWED_TRANSITIONS.get(event_type, {}).get(current_state, set())
    return target_state in allowed


def validate_event_transition(
    event_type: EventType,
    current_state: EventState,
    target_state: EventState,
) -> None:
    """이벤트 상태 전이 가능 여부를 검증한다."""

    if current_state == target_state:
        return
    if event_type not in _ALLOWED_TRANSITIONS:
        raise ValueError("이 이벤트 타입은 상태 전이를 지원하지 않습니다.")
    if not can_transition_event(event_type, current_state, target_state):
        raise ValueError(
            f"허용되지 않는 상태 전이입니다. {event_type.value} {current_state.value} -> {target_state.value}"
        )
