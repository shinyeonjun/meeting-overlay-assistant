"""히스토리 영역의 carry over service 서비스를 제공한다."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.services.events.event_management_service import EventManagementService

MAX_CARRY_OVER_PER_GROUP = 4


@dataclass(frozen=True)
class HistoryCarryOver:
    """맥락 기준 이어보기 브리프."""

    decisions: tuple[MeetingEvent, ...]
    action_items: tuple[MeetingEvent, ...]
    risks: tuple[MeetingEvent, ...]
    questions: tuple[MeetingEvent, ...]


class CarryOverService:
    """최근 세션 이벤트를 바탕으로 carry-over 브리프를 계산한다."""

    def __init__(self, event_management_service: EventManagementService) -> None:
        self._event_management_service = event_management_service

    def build(self, sessions: Iterable[object]) -> HistoryCarryOver:
        """최근 세션 목록에서 이어볼 핵심 이벤트만 추린다."""

        decisions: list[MeetingEvent] = []
        action_items: list[MeetingEvent] = []
        risks: list[MeetingEvent] = []
        questions: list[MeetingEvent] = []
        seen_keys: set[tuple[str, str]] = set()

        for session in sessions:
            session_events = self._event_management_service.list_events(session.id)
            ordered = sorted(session_events, key=lambda item: item.updated_at_ms, reverse=True)
            for event in ordered:
                if event.event_type == EventType.DECISION and event.state in {
                    EventState.CONFIRMED,
                    EventState.UPDATED,
                    EventState.CLOSED,
                }:
                    self._append_event(decisions, seen_keys=seen_keys, event=event)
                elif event.event_type == EventType.ACTION_ITEM and event.state in {
                    EventState.OPEN,
                    EventState.CLOSED,
                }:
                    self._append_event(action_items, seen_keys=seen_keys, event=event)
                elif event.event_type == EventType.RISK and event.state in {
                    EventState.OPEN,
                    EventState.RESOLVED,
                    EventState.CLOSED,
                }:
                    self._append_event(risks, seen_keys=seen_keys, event=event)
                elif event.event_type == EventType.QUESTION and event.state in {
                    EventState.OPEN,
                    EventState.ANSWERED,
                    EventState.CLOSED,
                }:
                    self._append_event(questions, seen_keys=seen_keys, event=event)

        return HistoryCarryOver(
            decisions=tuple(decisions),
            action_items=tuple(action_items),
            risks=tuple(risks),
            questions=tuple(questions),
        )

    @staticmethod
    def _append_event(
        bucket: list[MeetingEvent],
        *,
        seen_keys: set[tuple[str, str]],
        event: MeetingEvent,
    ) -> None:
        if len(bucket) >= MAX_CARRY_OVER_PER_GROUP:
            return

        dedupe_key = (event.event_type.value, event.normalized_title)
        if dedupe_key in seen_keys:
            return

        seen_keys.add(dedupe_key)
        bucket.append(event)
