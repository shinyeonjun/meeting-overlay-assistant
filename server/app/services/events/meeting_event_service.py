"""회의 이벤트 저장, 병합, 보정을 담당하는 서비스."""

from __future__ import annotations

from dataclasses import replace

from server.app.core.persistence_types import ConnectionLike
from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import EventType
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)


class MeetingEventService:
    """이벤트 저장과 중복 병합, 발화 단위 보정을 담당한다."""

    def __init__(self, event_repository: MeetingEventRepository) -> None:
        self._event_repository = event_repository

    def save_or_merge(
        self,
        candidate: MeetingEvent,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent:
        """새 이벤트를 저장하거나 기존 이벤트인지 병합한다."""
        same_source_event = self._find_same_source_event(
            candidate,
            connection=connection,
        )
        if same_source_event is not None:
            merged_same_source_event = self._merge_same_source_event(
                same_source_event,
                candidate,
            )
            return self._event_repository.update(
                merged_same_source_event,
                connection=connection,
            )

        existing = self._find_merge_target(candidate, connection=connection)
        if existing is None:
            return self._event_repository.save(candidate, connection=connection)

        merged_event = existing.merge_with(candidate)
        return self._event_repository.update(merged_event, connection=connection)

    def apply_source_utterance_corrections(
        self,
        *,
        session_id: str,
        source_utterance_id: str,
        corrected_events: list[MeetingEvent],
        target_event_types: tuple[EventType, ...],
        connection: ConnectionLike | None = None,
    ) -> list[MeetingEvent]:
        """특정 발화에서 파생된 이벤트를 보정 결과로 교체한다."""
        target_type_values = {event_type.value for event_type in target_event_types}
        existing_events = self._event_repository.list_by_source_utterance(
            session_id,
            source_utterance_id,
            insight_scope=corrected_events[0].insight_scope if corrected_events else "live",
            connection=connection,
        )
        existing_by_type = {
            event.event_type.value: event
            for event in existing_events
            if event.event_type.value in target_type_values
        }

        persisted_events: list[MeetingEvent] = []
        corrected_type_values: set[str] = set()
        for corrected_event in corrected_events:
            if corrected_event.event_type.value not in target_type_values:
                continue

            corrected_type_values.add(corrected_event.event_type.value)
            existing_event = existing_by_type.get(corrected_event.event_type.value)
            if existing_event is None:
                persisted_events.append(
                    self._event_repository.save(corrected_event, connection=connection)
                )
                continue

            updated_event = replace(
                existing_event,
                title=corrected_event.title,
                body=corrected_event.body,
                state=corrected_event.state,
                speaker_label=corrected_event.speaker_label or existing_event.speaker_label,
                evidence_text=corrected_event.evidence_text or existing_event.evidence_text,
                updated_at_ms=corrected_event.updated_at_ms,
            )
            persisted_events.append(
                self._event_repository.update(updated_event, connection=connection)
            )

        for event_type_value, existing_event in existing_by_type.items():
            if event_type_value in corrected_type_values:
                continue
            self._event_repository.delete(existing_event.id, connection=connection)

        return persisted_events

    def _find_merge_target(
        self,
        candidate: MeetingEvent,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent | None:
        existing = self._event_repository.find_merge_target(
            candidate,
            connection=connection,
        )
        if existing is not None and existing.can_merge_with(candidate):
            return existing
        return None

    def _find_same_source_event(
        self,
        candidate: MeetingEvent,
        *,
        connection: ConnectionLike | None = None,
    ) -> MeetingEvent | None:
        if not candidate.source_utterance_id:
            return None

        existing_events = self._event_repository.list_by_source_utterance(
            candidate.session_id,
            candidate.source_utterance_id,
            insight_scope=candidate.insight_scope,
            connection=connection,
        )
        for existing_event in reversed(existing_events):
            if existing_event.event_type == candidate.event_type:
                return existing_event
        return None

    @staticmethod
    def _merge_same_source_event(
        existing: MeetingEvent,
        candidate: MeetingEvent,
    ) -> MeetingEvent:
        merged = existing.merge_with(candidate)
        return replace(
            merged,
            title=candidate.title or merged.title,
            body=candidate.body or merged.body,
            speaker_label=candidate.speaker_label or merged.speaker_label,
            evidence_text=candidate.evidence_text or merged.evidence_text,
            input_source=candidate.input_source or merged.input_source,
            updated_at_ms=candidate.updated_at_ms,
        )
