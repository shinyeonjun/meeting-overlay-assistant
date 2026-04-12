"""Final lane에서 segment를 전사하고 필터링하는 helper를 모아둔다.

이 모듈은 chunk를 바로 저장하지 않는다. segment를 잘라서 STT에 넘기고,
guard, 중복 검사, short-final 필터를 통과한 결과만 persistence 단계로
넘기는 전처리 역할에 집중한다.
"""
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
    """처리 가능한 segment만 골라 final utterance 저장 단계로 넘긴다.

    final lane의 핵심 루프다. segment를 하나씩 전사하고, 거절 사유가 있으면
    즉시 버린 뒤, 통과한 결과만 persistence helper로 전달한다.
    """

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
    """Segmenter와 content gate를 모두 통과한 segment만 내보낸다.

    content gate는 너무 짧거나 무의미한 오디오를 빠르게 배제하는 첫 번째
    방어선이다. 여기서 걸러야 STT 호출 수와 후속 노이즈가 줄어든다.
    """

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
    """Segment 전사와 final queue delay 계산을 한 번에 수행한다.

    queue delay는 "segment가 끝난 시점"과 "실제 final 처리 시점"의 차이이며,
    live final emit 여부와 preview backpressure 판단에 같이 쓰인다.
    """

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
    """전사 결과가 저장 가치가 있는지 검사한다.

    먼저 일반 transcription guard에서 막는 문구, 무음, 저품질 결과인지
    확인하고, 짧은 final은 별도 confidence 기준으로 한 번 더 거른다.
    """

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
    """Final 전사 거절 사유를 로그와 런타임 모니터에 남긴다."""

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
