"""Preview utterance 조립 helper."""

from __future__ import annotations

import logging

from server.app.services.audio.pipeline.models.live_stream_utterance import LiveStreamUtterance


logger = logging.getLogger(__name__)


def build_preview_utterance_payloads(
    service,
    *,
    session_id: str,
    input_source: str | None,
    preview_cycle_id: int | None,
    preview_results,
) -> list[LiveStreamUtterance]:
    """Preview 결과를 실시간 utterance payload로 조립한다."""

    now_ms = service._now_ms()
    preview_utterances: list[LiveStreamUtterance] = []
    preview_seq_num: int | None = None
    preview_segment_id: str | None = None
    accepted_results = []

    for result in preview_results:
        normalized_text = service._normalize_text(result.text)
        if not normalized_text:
            continue

        keep_preview, rejection_reason = service._transcription_guard.evaluate(result)
        if not keep_preview:
            logger.info(
                "preview 전사 필터링: session_id=%s reason=%s confidence=%.4f no_speech_prob=%s text=%s",
                session_id,
                rejection_reason,
                result.confidence,
                (
                    f"{result.no_speech_prob:.4f}"
                    if result.no_speech_prob is not None
                    else "none"
                ),
                result.text,
            )
            if service._runtime_monitor_service is not None:
                service._runtime_monitor_service.record_preview_rejection(
                    session_id=session_id,
                    reason=rejection_reason,
                    filter_stage="guard",
                )
            continue

        keep_preview_length, preview_rejection_reason = should_keep_preview(service, result)
        if not keep_preview_length:
            logger.info(
                "preview 전사 필터링: session_id=%s reason=%s confidence=%.4f no_speech_prob=%s text=%s",
                session_id,
                preview_rejection_reason,
                result.confidence,
                (
                    f"{result.no_speech_prob:.4f}"
                    if result.no_speech_prob is not None
                    else "none"
                ),
                result.text,
            )
            if service._runtime_monitor_service is not None:
                service._runtime_monitor_service.record_preview_rejection(
                    session_id=session_id,
                    reason=preview_rejection_reason,
                    filter_stage="length",
                )
            continue

        accepted_results.append(result)

    reduced_results = reduce_preview_results(service, accepted_results)

    for result in reduced_results:
        if preview_seq_num is None or preview_segment_id is None:
            preview_seq_num, preview_segment_id = service._coordination_state.get_or_create_preview_binding()

        preview_utterances.append(
            LiveStreamUtterance.create(
                seq_num=preview_seq_num,
                segment_id=preview_segment_id,
                start_ms=now_ms,
                end_ms=now_ms,
                text=result.text,
                confidence=result.confidence,
                kind=result.kind,
                revision=result.revision,
                input_source=input_source,
                stability=getattr(result, "stability", None),
            )
        )
        if service._runtime_monitor_service is not None:
            service._runtime_monitor_service.record_preview_emitted(
                session_id=session_id,
                kind=getattr(result, "kind", "preview"),
                preview_cycle_id=preview_cycle_id,
            )

    if preview_utterances:
        if len(accepted_results) > len(preview_utterances):
            logger.debug(
                "preview 결과 병합: session_id=%s raw=%d emitted=%d",
                session_id,
                len(accepted_results),
                len(preview_utterances),
            )
        if preview_seq_num is not None and preview_segment_id is not None:
            service._coordination_state.mark_preview_emitted(
                seq_num=preview_seq_num,
                segment_id=preview_segment_id,
                now_ms=now_ms,
            )
        for utterance in preview_utterances:
            if utterance.kind == "live_final":
                remember_live_final_candidate(
                    service,
                    segment_id=utterance.segment_id,
                    text=utterance.text,
                    emitted_at_ms=now_ms,
                )

    return preview_utterances


def should_keep_preview(service, result) -> tuple[bool, str | None]:
    """Preview 길이 조건을 검사한다."""

    preview_length = service._compact_length(result.text)
    if preview_length < service._preview_min_compact_length:
        return False, "preview_too_short"
    return True, None


def reduce_preview_results(service, results) -> list:
    """같은 preview 사이클의 증분 결과를 대표 후보 위주로 줄인다."""

    reduced_results = []
    for result in results:
        if not reduced_results:
            reduced_results.append(result)
            continue

        previous = reduced_results[-1]
        if should_merge_preview_result(service, previous, result):
            reduced_results[-1] = result
            continue

        reduced_results.append(result)

    return reduced_results


def should_merge_preview_result(service, previous, current) -> bool:
    """증분 preview나 live_final 승격이면 같은 줄로 간주한다."""

    previous_text = service._normalize_text(previous.text)
    current_text = service._normalize_text(current.text)
    if not previous_text or not current_text:
        return False

    if current.kind == "live_final":
        return True
    if previous.kind == "live_final":
        return False
    if current_text == previous_text:
        return True
    if current_text.startswith(previous_text) or previous_text.startswith(current_text):
        return True
    return False


def remember_live_final_candidate(
    service,
    *,
    segment_id: str,
    text: str,
    emitted_at_ms: int,
) -> None:
    """live_final 후보를 archive_final 비교용으로 보관한다."""

    normalized_text = service._normalize_text(text)
    if not segment_id or not normalized_text:
        return
    service._coordination_state.remember_live_final_candidate(
        segment_id=segment_id,
        text=normalized_text,
        emitted_at_ms=emitted_at_ms,
    )
