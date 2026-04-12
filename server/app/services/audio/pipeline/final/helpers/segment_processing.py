"""오디오 영역의 segment processing 서비스를 제공한다."""
from __future__ import annotations

import logging

from server.app.services.audio.pipeline.final.helpers.monitoring import (
    apply_preview_backpressure,
)
from server.app.services.audio.pipeline.final.helpers.persistence import (
    save_final_utterance_and_events,
    should_skip_duplicate_transcription,
)


logger = logging.getLogger(__name__)


def process_segments(
    service,
    *,
    session_id: str,
    chunk: bytes,
    input_source: str | None,
    saved_utterances,
    outgoing_final_utterances,
    saved_events,
    connection,
) -> None:
    """처리 가능한 세그먼트를 순회하며 final/archive 결과를 만든다."""

    for segment in iter_processable_segments(service, session_id=session_id, chunk=chunk):
        transcription, final_queue_delay_ms = transcribe_segment(
            service,
            session_id=session_id,
            segment=segment,
        )

        if is_rejected_transcription(service, session_id=session_id, transcription=transcription):
            continue

        if should_skip_duplicate_transcription(
            service,
            session_id=session_id,
            text=transcription.text,
            confidence=transcription.confidence,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            connection=connection,
        ):
            logger.info(
                "인접 중복 전사 스킵: session_id=%s confidence=%.4f text=%s",
                session_id,
                transcription.confidence,
                transcription.text,
            )
            continue

        save_final_utterance_and_events(
            service,
            session_id=session_id,
            segment=segment,
            transcription=transcription,
            final_queue_delay_ms=final_queue_delay_ms,
            input_source=input_source,
            saved_utterances=saved_utterances,
            outgoing_final_utterances=outgoing_final_utterances,
            saved_events=saved_events,
            connection=connection,
        )


def iter_processable_segments(service, *, session_id: str, chunk: bytes):
    """content gate를 통과한 세그먼트만 순회한다."""

    for segment in service._final_lane_state.segmenter.split(chunk):
        logger.debug(
            "세그먼트 처리: session_id=%s start_ms=%s end_ms=%s bytes=%d",
            session_id,
            segment.start_ms,
            segment.end_ms,
            len(segment.raw_bytes),
        )
        if service._content_gate is not None and not service._content_gate.should_process(segment):
            logger.info(
                "오디오 content gate 차단: session_id=%s start_ms=%s end_ms=%s",
                session_id,
                segment.start_ms,
                segment.end_ms,
            )
            continue
        yield segment


def transcribe_segment(service, *, session_id: str, segment):
    """Final lane 전사와 queue delay 계산을 수행한다."""

    transcription = service._final_lane_state.speech_to_text_service.transcribe(segment)
    final_queue_delay_ms = max(service._now_ms() - segment.end_ms, 0)
    logger.info(
        "전사 결과: session_id=%s start_ms=%s end_ms=%s final_queue_delay_ms=%s confidence=%.4f no_speech_prob=%s text=%s",
        session_id,
        segment.start_ms,
        segment.end_ms,
        final_queue_delay_ms,
        transcription.confidence,
        (
            f"{transcription.no_speech_prob:.4f}"
            if transcription.no_speech_prob is not None
            else "none"
        ),
        transcription.text,
    )
    apply_preview_backpressure(
        service,
        session_id=session_id,
        final_queue_delay_ms=final_queue_delay_ms,
    )
    return transcription, final_queue_delay_ms


def is_rejected_transcription(service, *, session_id: str, transcription) -> bool:
    """guard와 short-final 조건을 통과하는지 검사한다."""

    keep_transcription, rejection_reason = service._transcription_guard.evaluate(transcription)
    if not keep_transcription:
        log_transcription_rejection(service, session_id, rejection_reason, transcription)
        return True

    keep_short_final, short_final_reason = service._should_keep_short_final(transcription)
    if not keep_short_final:
        log_transcription_rejection(service, session_id, short_final_reason, transcription)
        return True
    return False


def log_transcription_rejection(service, session_id: str, reason: str | None, transcription) -> None:
    """Final 전사 필터링 사유를 로그와 모니터에 남긴다."""

    logger.info(
        "전사 필터링: session_id=%s reason=%s confidence=%.4f no_speech_prob=%s text=%s",
        session_id,
        reason,
        transcription.confidence,
        (
            f"{transcription.no_speech_prob:.4f}"
            if transcription.no_speech_prob is not None
            else "none"
        ),
        transcription.text,
    )
    if service._runtime_monitor_service is not None:
        service._runtime_monitor_service.record_rejection(reason=reason)
