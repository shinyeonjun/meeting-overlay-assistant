"""공통 영역의 event type policy 서비스를 제공한다."""
from __future__ import annotations

from collections.abc import Iterable

from server.app.domain.shared.enums import EventType


INSIGHT_EVENT_TYPES: tuple[EventType, ...] = (
    EventType.TOPIC,
    EventType.QUESTION,
    EventType.DECISION,
    EventType.ACTION_ITEM,
    EventType.RISK,
)

INSIGHT_EVENT_TYPE_VALUES: tuple[str, ...] = tuple(
    event_type.value for event_type in INSIGHT_EVENT_TYPES
)
_INSIGHT_EVENT_TYPE_VALUE_SET: frozenset[str] = frozenset(INSIGHT_EVENT_TYPE_VALUES)


def normalize_event_type_token(value: object) -> str:
    """event_type 토큰을 비교 가능한 포맷으로 정규화한다."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace(" ", "_")


def filter_insight_event_type_values(values: Iterable[object]) -> tuple[str, ...]:
    """입력 목록에서 인사이트 이벤트 타입만 필터링한다."""
    filtered: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_event_type_token(value)
        if normalized not in _INSIGHT_EVENT_TYPE_VALUE_SET:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(normalized)
    if filtered:
        return tuple(filtered)
    return INSIGHT_EVENT_TYPE_VALUES
