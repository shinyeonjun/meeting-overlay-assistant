"""Meeting event repository 매핑 helper."""

from __future__ import annotations

from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    epoch_ms_to_timestamptz,
    timestamptz_to_epoch_ms,
)


def build_insert_values(event: MeetingEvent) -> tuple[object, ...]:
    """이벤트 INSERT 파라미터 튜플을 만든다."""

    return (
        event.id,
        event.session_id,
        event.source_utterance_id,
        event.event_type.value,
        event.title,
        event.normalized_title,
        event.body,
        event.evidence_text,
        event.speaker_label,
        event.state.value,
        event.input_source,
        event.insight_scope,
        event.event_source,
        event.processing_job_id,
        epoch_ms_to_timestamptz(event.created_at_ms),
        epoch_ms_to_timestamptz(event.updated_at_ms),
        epoch_ms_to_timestamptz(event.finalized_at_ms),
    )


def build_update_values(event: MeetingEvent) -> tuple[object, ...]:
    """이벤트 UPDATE 파라미터 튜플을 만든다."""

    return (
        event.source_utterance_id,
        event.event_type.value,
        event.title,
        event.normalized_title,
        event.body,
        event.evidence_text,
        event.speaker_label,
        event.state.value,
        event.input_source,
        event.insight_scope,
        event.event_source,
        event.processing_job_id,
        epoch_ms_to_timestamptz(event.created_at_ms),
        epoch_ms_to_timestamptz(event.updated_at_ms),
        epoch_ms_to_timestamptz(event.finalized_at_ms),
        event.id,
    )


def row_to_event(row) -> MeetingEvent:
    """DB row를 MeetingEvent 도메인 객체로 변환한다."""

    return MeetingEvent(
        id=row["id"],
        session_id=row["session_id"],
        event_type=EventType(row["event_type"]),
        title=row["title"],
        body=row["body"],
        evidence_text=row["evidence_text"],
        speaker_label=row["speaker_label"],
        state=EventState(row["state"]),
        source_utterance_id=row["source_utterance_id"],
        created_at_ms=timestamptz_to_epoch_ms(row["created_at_ms"]),
        updated_at_ms=timestamptz_to_epoch_ms(row["updated_at_ms"]),
        input_source=row["input_source"],
        insight_scope=row["insight_scope"],
        event_source=row["event_source"] if "event_source" in row else "live",
        processing_job_id=row["processing_job_id"] if "processing_job_id" in row else None,
        finalized_at_ms=(
            timestamptz_to_epoch_ms(row["finalized_at_ms"])
            if "finalized_at_ms" in row and row["finalized_at_ms"] is not None
            else None
        ),
    )
