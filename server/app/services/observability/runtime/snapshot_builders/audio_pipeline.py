"""공통 영역의 audio pipeline 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.observability.runtime.snapshot_builders.preview import (
    build_preview_metrics,
)


def build_audio_pipeline_metrics(
    *,
    finals: list[dict[str, object]],
    previews: list[dict[str, object]],
    preview_cycles: list[dict[str, object]],
    chunks: list[dict[str, object]],
    rejections: list[dict[str, object]],
    backpressure: list[dict[str, object]],
    errors: list[dict[str, object]],
    last_chunk_processed_at: str | None,
    last_error_at: str | None,
    last_error_message: str | None,
) -> dict[str, object]:
    """audio_pipeline snapshot 필드를 계산한다."""

    queue_delays = [
        int(item["final_queue_delay_ms"])
        for item in finals
        if isinstance(item.get("final_queue_delay_ms"), int)
    ]
    recent_utterance_count = sum(
        int(item["utterance_count"])
        for item in chunks
        if isinstance(item.get("utterance_count"), int)
    )
    recent_event_count = sum(
        int(item["event_count"])
        for item in chunks
        if isinstance(item.get("event_count"), int)
    )
    matched_count = sum(1 for item in finals if item.get("alignment_status") == "matched")
    grace_matched_count = sum(
        1 for item in finals if item.get("alignment_status") == "grace_matched"
    )
    standalone_count = sum(
        1 for item in finals if item.get("alignment_status") == "standalone_final"
    )
    final_count = len(finals)
    live_final_compares = [
        item for item in finals if int(item.get("live_final_compare_count") or 0) > 0
    ]
    live_final_compare_count = len(live_final_compares)
    live_final_changed_count = sum(
        1 for item in live_final_compares if item.get("live_final_changed") is True
    )
    live_final_similarity_values = [
        float(item["live_final_similarity"])
        for item in live_final_compares
        if isinstance(item.get("live_final_similarity"), (int, float))
    ]
    live_final_delay_values = [
        int(item["live_final_delay_ms"])
        for item in live_final_compares
        if isinstance(item.get("live_final_delay_ms"), int)
    ]
    preview_metrics = build_preview_metrics(
        previews=previews,
        preview_cycles=preview_cycles,
    )

    return {
        "recent_final_count": final_count,
        "recent_utterance_count": recent_utterance_count,
        "recent_event_count": recent_event_count,
        "average_queue_delay_ms": (
            round(sum(queue_delays) / len(queue_delays), 1) if queue_delays else None
        ),
        "max_queue_delay_ms": max(queue_delays) if queue_delays else None,
        "late_final_count": sum(
            1 for item in finals if item.get("emitted_live_final") is False
        ),
        "backpressure_count": len(backpressure),
        "filtered_count": len(rejections),
        "error_count": len(errors),
        "matched_count": matched_count,
        "grace_matched_count": grace_matched_count,
        "standalone_count": standalone_count,
        "standalone_ratio": round(standalone_count / final_count, 2) if final_count else 0.0,
        "live_final_compare_count": live_final_compare_count,
        "live_final_exact_match_count": live_final_compare_count - live_final_changed_count,
        "live_final_changed_count": live_final_changed_count,
        "live_final_change_ratio": (
            round(live_final_changed_count / live_final_compare_count, 2)
            if live_final_compare_count
            else 0.0
        ),
        "live_final_average_similarity": (
            round(sum(live_final_similarity_values) / len(live_final_similarity_values), 3)
            if live_final_similarity_values
            else None
        ),
        "live_final_average_delay_ms": (
            round(sum(live_final_delay_values) / len(live_final_delay_values), 1)
            if live_final_delay_values
            else None
        ),
        **preview_metrics,
        "last_chunk_processed_at": last_chunk_processed_at,
        "last_error_at": last_error_at,
        "last_error_message": last_error_message,
    }
