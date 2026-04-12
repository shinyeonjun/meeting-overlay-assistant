"""오디오 영역의 persistence 서비스를 제공한다."""
from __future__ import annotations

import logging
from dataclasses import replace
from difflib import SequenceMatcher

from server.app.domain.events import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventType
from server.app.services.audio.pipeline.models.live_stream_utterance import (
    LiveStreamUtterance,
)
from server.app.services.audio.pipeline.preview.preview_flow import (
    consume_live_final_comparison,
)


logger = logging.getLogger(__name__)

_LIVE_EVENT_TYPES = {EventType.QUESTION}


def save_final_utterance_and_events(
    service,
    *,
    session_id: str,
    segment,
    transcription,
    final_queue_delay_ms: int,
    input_source: str | None,
    saved_utterances,
    outgoing_final_utterances,
    saved_events,
    connection,
) -> None:
    """Final utterance를 만들고 websocket용 결과와 live 이벤트를 구성한다."""

    utterance = Utterance.create(
        session_id=session_id,
        seq_num=_resolve_next_utterance_sequence(
            service,
            session_id=session_id,
            connection=connection,
        ),
        start_ms=segment.start_ms,
        end_ms=segment.end_ms,
        text=transcription.text,
        confidence=transcription.confidence,
        input_source=input_source,
        stt_backend=service._resolve_stt_backend_name(),
        latency_ms=final_queue_delay_ms,
    )
    saved_utterance = _persist_or_keep_runtime_utterance(
        service,
        utterance=utterance,
        connection=connection,
    )
    saved_utterances.append(saved_utterance)
    segment_id, outgoing_seq_num, alignment_status = consume_segment_binding_for_final(
        service,
        saved_utterance,
    )
    live_final_comparison = consume_live_final_comparison(
        service,
        segment_id=segment_id,
        archive_text=saved_utterance.text,
        archive_emitted_at_ms=service._now_ms(),
    )
    emitted_live_final = service._should_emit_live_final(final_queue_delay_ms)
    final_kind = "archive_final" if emitted_live_final else "late_archive_final"
    outgoing_final_utterances.append(
        LiveStreamUtterance.from_utterance(
            saved_utterance,
            segment_id=segment_id,
            seq_num=outgoing_seq_num,
            input_source=input_source,
            kind=final_kind,
            stability=("final" if not emitted_live_final else None),
        )
    )

    logger.debug(
        "발화 처리 완료: session_id=%s utterance_id=%s seq_num=%d segment_id=%s alignment=%s confidence=%.4f",
        session_id,
        saved_utterance.id,
        saved_utterance.seq_num,
        segment_id,
        alignment_status,
        saved_utterance.confidence,
    )
    logger.info(
        "segment 정합성: session_id=%s segment_id=%s alignment=%s final_queue_delay_ms=%s",
        session_id,
        segment_id,
        alignment_status,
        final_queue_delay_ms,
    )
    if not emitted_live_final:
        logger.info(
            "late final로 다운그레이드 전송: session_id=%s segment_id=%s final_queue_delay_ms=%s max_live_delay_ms=%s",
            session_id,
            segment_id,
            final_queue_delay_ms,
            service._resolve_live_final_delay_threshold_ms(),
        )
    service._record_alignment_status(session_id, alignment_status)
    if service._runtime_monitor_service is not None:
        service._runtime_monitor_service.record_final_transcription(
            session_id=session_id,
            final_queue_delay_ms=final_queue_delay_ms,
            emitted_live_final=emitted_live_final,
            alignment_status=alignment_status,
            live_final_compare_count=(1 if live_final_comparison is not None else 0),
            live_final_changed=(
                bool(live_final_comparison["changed"])
                if live_final_comparison is not None
                else False
            ),
            live_final_similarity=(
                float(live_final_comparison["similarity"])
                if live_final_comparison is not None
                else None
            ),
            live_final_delay_ms=(
                int(live_final_comparison["delay_ms"])
                if live_final_comparison is not None
                else None
            ),
        )
    service._final_lane_state.processed_final_count += 1

    if not service._live_question_analysis_enabled:
        for event in service._analyzer_service.analyze(saved_utterance):
            event_candidate = event
            if event_candidate.event_type not in _LIVE_EVENT_TYPES:
                continue
            if not event_candidate.evidence_text:
                event_candidate = replace(
                    event_candidate,
                    evidence_text=saved_utterance.text,
                )
            if event_candidate.input_source != input_source:
                event_candidate = replace(
                    event_candidate,
                    input_source=input_source,
                )
            if event_candidate.insight_scope != "live":
                event_candidate = replace(event_candidate, insight_scope="live")
            saved_event = _persist_or_keep_runtime_event(
                service,
                candidate=event_candidate,
                connection=connection,
            )
            existing_index = next(
                (
                    index
                    for index, existing_event in enumerate(saved_events)
                    if existing_event.id == saved_event.id
                ),
                None,
            )
            if existing_index is None:
                saved_events.append(saved_event)
            else:
                saved_events[existing_index] = saved_event
            logger.debug(
                "이벤트 처리 완료: session_id=%s event_id=%s type=%s state=%s",
                session_id,
                saved_event.id,
                saved_event.event_type.value,
                saved_event.state.value,
            )


def consume_segment_binding_for_final(
    service,
    utterance: Utterance,
) -> tuple[str, int | None, str]:
    """Preview와 final 사이의 segment binding을 소비한다."""

    return service._coordination_state.consume_for_final(
        now_ms=service._now_ms(),
        start_ms=utterance.start_ms,
        end_ms=utterance.end_ms,
    )


def should_skip_duplicate_transcription(
    service,
    *,
    session_id: str,
    text: str,
    confidence: float,
    start_ms: int,
    end_ms: int,
    connection,
) -> bool:
    """인접한 중복 전사를 필터링한다."""

    if service._duplicate_window_ms <= 0:
        return False
    if confidence > service._duplicate_max_confidence:
        return False

    normalized_text = service._normalize_text(text)
    if not normalized_text:
        return False

    recent_utterances = _list_recent_utterances(
        service,
        session_id=session_id,
        limit=2,
        connection=connection,
    )
    for recent_utterance in recent_utterances:
        if recent_utterance.confidence > service._duplicate_max_confidence:
            continue
        if abs(start_ms - recent_utterance.end_ms) > service._duplicate_window_ms:
            continue
        recent_text = service._normalize_text(recent_utterance.text)
        if not recent_text:
            continue
        similarity = SequenceMatcher(a=normalized_text, b=recent_text).ratio()
        if similarity >= service._duplicate_similarity_threshold:
            return True

    return False


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
