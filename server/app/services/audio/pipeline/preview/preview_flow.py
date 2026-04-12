"""Preview/live_final 생성 흐름."""

from __future__ import annotations

from server.app.services.audio.pipeline.models.live_stream_utterance import LiveStreamUtterance
from server.app.services.audio.pipeline.preview.preview_helpers import (
    build_preview_utterance_payloads,
    collect_preview_results,
    consume_early_eou_hint,
    consume_live_final_comparison,
    remember_live_final_candidate,
    should_keep_preview,
)


def build_preview_utterances(
    service,
    session_id: str,
    chunk: bytes,
    *,
    input_source: str | None,
    preview_cycle_id: int | None,
) -> list[LiveStreamUtterance]:
    """Preview lane에서 실시간 발화를 생성한다."""

    preview_results = collect_preview_results(
        service,
        session_id=session_id,
        chunk=chunk,
        preview_cycle_id=preview_cycle_id,
    )
    if not preview_results:
        return []

    return build_preview_utterance_payloads(
        service,
        session_id=session_id,
        input_source=input_source,
        preview_cycle_id=preview_cycle_id,
        preview_results=preview_results,
    )


__all__ = [
    "build_preview_utterances",
    "consume_early_eou_hint",
    "consume_live_final_comparison",
    "remember_live_final_candidate",
    "should_keep_preview",
]
