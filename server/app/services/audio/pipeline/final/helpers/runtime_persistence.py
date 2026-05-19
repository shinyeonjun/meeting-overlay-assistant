"""Final lane ???/?? ?? ??."""

from __future__ import annotations

from dataclasses import replace

from server.app.domain.events import MeetingEvent
from server.app.domain.models.utterance import Utterance

def _resolve_next_utterance_sequence(service, *, session_id: str, connection) -> int:
    if service._persist_live_runtime_data:
        return service._utterance_repository.next_sequence(
            session_id,
            connection=connection,
        )

    current = int(service._runtime_next_final_seq_by_session.get(session_id, 1))
    service._runtime_next_final_seq_by_session[session_id] = current + 1
    return current


def _persist_or_keep_runtime_utterance(
    service,
    *,
    utterance: Utterance,
    connection,
) -> Utterance:
    if service._persist_live_runtime_data:
        return service._utterance_repository.save(utterance, connection=connection)

    recent_utterances = service._runtime_recent_final_utterances_by_session.setdefault(
        utterance.session_id,
        [],
    )
    recent_utterances.append(utterance)
    overflow = len(recent_utterances) - service._runtime_recent_final_utterance_limit
    if overflow > 0:
        del recent_utterances[:overflow]
    return utterance


def _list_recent_utterances(
    service,
    *,
    session_id: str,
    limit: int,
    connection,
) -> list[Utterance]:
    if service._persist_live_runtime_data:
        return service._utterance_repository.list_recent_by_session(
            session_id,
            limit=limit,
            connection=connection,
        )

    recent_utterances = service._runtime_recent_final_utterances_by_session.get(
        session_id,
        [],
    )
    if limit <= 0:
        return []
    return list(recent_utterances[-limit:])


def _persist_or_keep_runtime_event(
    service,
    *,
    candidate: MeetingEvent,
    connection,
) -> MeetingEvent:
    if service._persist_live_runtime_data:
        return service._event_service.save_or_merge(candidate, connection=connection)
    return _save_or_merge_runtime_event(service, candidate)


def _save_or_merge_runtime_event(service, candidate: MeetingEvent) -> MeetingEvent:
    session_events = service._runtime_live_events_by_session.setdefault(
        candidate.session_id,
        [],
    )

    same_source_index = _find_same_source_event_index(session_events, candidate)
    if same_source_index is not None:
        merged_event = _merge_same_source_event(
            session_events[same_source_index],
            candidate,
        )
        session_events[same_source_index] = merged_event
        return merged_event

    merge_target_index = _find_merge_target_index(session_events, candidate)
    if merge_target_index is not None:
        merged_event = session_events[merge_target_index].merge_with(candidate)
        session_events[merge_target_index] = merged_event
        return merged_event

    session_events.append(candidate)
    overflow = len(session_events) - service._runtime_live_event_limit
    if overflow > 0:
        del session_events[:overflow]
    return candidate


def _find_same_source_event_index(
    events: list[MeetingEvent],
    candidate: MeetingEvent,
) -> int | None:
    if not candidate.source_utterance_id:
        return None

    for index in range(len(events) - 1, -1, -1):
        existing = events[index]
        if existing.insight_scope != candidate.insight_scope:
            continue
        if existing.source_utterance_id != candidate.source_utterance_id:
            continue
        if existing.event_type != candidate.event_type:
            continue
        return index
    return None


def _find_merge_target_index(
    events: list[MeetingEvent],
    candidate: MeetingEvent,
) -> int | None:
    for index in range(len(events) - 1, -1, -1):
        existing = events[index]
        if existing.insight_scope != candidate.insight_scope:
            continue
        if existing.can_merge_with(candidate):
            return index
    return None


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
