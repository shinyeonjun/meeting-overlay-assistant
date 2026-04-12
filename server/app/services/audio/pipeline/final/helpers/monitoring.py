"""오디오 영역의 monitoring 서비스를 제공한다."""
from __future__ import annotations

import logging

from server.app.services.audio.pipeline.common.pipeline_text import resolve_stt_backend_name


logger = logging.getLogger(__name__)


def apply_preview_backpressure(service, *, session_id: str, final_queue_delay_ms: int) -> None:
    """Final queue delay에 따라 preview backpressure를 적용한다."""

    if not should_emit_live_final(service, final_queue_delay_ms):
        service._coordination_state.clear_preview_backpressure()
        return
    activated, hold_chunks = service._coordination_state.apply_final_queue_delay(
        final_queue_delay_ms
    )
    if not activated:
        return
    logger.info(
        "preview backpressure 활성화: final_queue_delay_ms=%d hold_chunks=%d",
        final_queue_delay_ms,
        hold_chunks,
    )
    if service._runtime_monitor_service is not None:
        service._runtime_monitor_service.record_preview_backpressure(
            session_id=session_id,
            final_queue_delay_ms=final_queue_delay_ms,
            hold_chunks=hold_chunks,
        )


def should_emit_live_final(service, final_queue_delay_ms: int) -> bool:
    """Final queue delay가 live emit 한계값을 넘는지 판단한다."""

    if service._live_final_emit_max_delay_ms <= 0:
        return True
    return final_queue_delay_ms <= resolve_live_final_delay_threshold_ms(service)


def resolve_live_final_delay_threshold_ms(service) -> int:
    """초기 grace 구간을 반영한 live final 허용 지연을 계산한다."""

    allowed_delay_ms = service._live_final_emit_max_delay_ms
    if (
        service._final_lane_state.processed_final_count < service._live_final_initial_grace_segments
        and service._live_final_initial_grace_delay_ms > allowed_delay_ms
    ):
        return service._live_final_initial_grace_delay_ms
    return allowed_delay_ms


def record_alignment_status(service, session_id: str, alignment_status: str) -> None:
    """Segment alignment 누적 상태를 기록한다."""

    counters = service._coordination_state.record_alignment(alignment_status)
    logger.info(
        "segment 정합도 누적: session_id=%s matched=%d grace_matched=%d standalone=%d standalone_ratio=%.2f",
        session_id,
        counters.matched,
        counters.grace_matched,
        counters.standalone,
        counters.standalone_ratio,
    )


def should_keep_short_final(service, result) -> tuple[bool, str | None]:
    """짧은 final의 confidence 조건을 검사한다."""

    if service._final_short_text_max_compact_length <= 0:
        return True, None
    final_length = service._compact_length(result.text)
    if final_length > service._final_short_text_max_compact_length:
        return True, None
    if result.confidence >= service._final_short_text_min_confidence:
        return True, None
    return False, "short_final_low_confidence"


def record_chunk_processed(service, *, session_id: str, utterance_count: int, event_count: int) -> None:
    """Runtime monitor에 chunk 처리 결과를 남긴다."""

    if service._runtime_monitor_service is None:
        return
    service._runtime_monitor_service.record_chunk_processed(
        session_id=session_id,
        utterance_count=utterance_count,
        event_count=event_count,
    )


def record_processing_error(service, scope: str, message: str) -> None:
    """Runtime monitor에 처리 오류를 남긴다."""

    if service._runtime_monitor_service is None:
        return
    service._runtime_monitor_service.record_error(scope=scope, message=message)


def resolve_backend_name(service) -> str:
    """Final lane의 STT 백엔드 이름을 반환한다."""

    return resolve_stt_backend_name(service._final_lane_state.speech_to_text_service)
