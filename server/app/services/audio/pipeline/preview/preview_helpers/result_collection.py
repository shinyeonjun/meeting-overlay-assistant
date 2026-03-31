"""Preview result 수집 helper."""

from __future__ import annotations

import logging
from dataclasses import replace

from server.app.services.audio.stt.transcription import (
    pop_preview_runtime_context,
    push_preview_runtime_context,
)


logger = logging.getLogger(__name__)


def collect_preview_results(
    service,
    session_id: str,
    chunk: bytes,
    *,
    preview_cycle_id: int | None,
):
    """Preview service에서 원시 preview/live_final 후보를 수집한다."""

    preview_service = service._preview_lane_state.speech_to_text_service
    if preview_service is None:
        return []

    should_suppress_preview, remaining_chunks = service._coordination_state.tick_preview_backpressure()
    if should_suppress_preview:
        logger.info(
            "preview 전사 억제: reason=backpressure remaining_chunks=%d",
            remaining_chunks,
        )
        return []

    preview_context_tokens = push_preview_runtime_context(
        session_id=session_id,
        runtime_monitor_service=service._runtime_monitor_service,
        preview_cycle_id=preview_cycle_id,
    )
    try:
        preview_results = preview_service.preview_chunk(chunk)
    finally:
        pop_preview_runtime_context(preview_context_tokens)

    if not preview_results:
        return []

    if consume_early_eou_hint(service):
        promoted_result = preview_results[-1]
        if getattr(promoted_result, "kind", "preview") == "preview":
            preview_results[-1] = replace(
                promoted_result,
                kind="live_final",
                stability="medium",
            )

    if service._runtime_monitor_service is not None:
        for result in preview_results:
            service._runtime_monitor_service.record_preview_candidate(
                session_id=session_id,
                kind=getattr(result, "kind", "preview"),
                preview_cycle_id=preview_cycle_id,
            )

    return preview_results


def consume_early_eou_hint(service) -> bool:
    """segmenter의 early end-of-utterance 힌트를 소비한다."""

    consume_hint = getattr(service._final_lane_state.segmenter, "consume_early_eou_hint", None)
    if not callable(consume_hint):
        return False
    return bool(consume_hint())
