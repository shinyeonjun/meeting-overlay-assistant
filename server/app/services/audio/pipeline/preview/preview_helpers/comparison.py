"""Preview/live_final 비교 helper."""

from __future__ import annotations

from difflib import SequenceMatcher

from server.app.services.audio.pipeline.common.pipeline_text import normalize_text


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


def consume_live_final_comparison(
    service,
    *,
    segment_id: str,
    archive_text: str,
    archive_emitted_at_ms: int,
) -> dict[str, object] | None:
    """archive_final 도착 시 live_final과의 차이를 계산한다."""

    if not segment_id:
        return None
    candidate = service._coordination_state.consume_live_final_candidate(
        segment_id=segment_id,
    )
    if candidate is None:
        return None

    live_text = str(candidate.get("text") or "")
    normalized_archive_text = normalize_text(archive_text)
    if not live_text or not normalized_archive_text:
        return None

    similarity = SequenceMatcher(None, live_text, normalized_archive_text).ratio()
    changed = live_text != normalized_archive_text
    emitted_at_ms = int(candidate.get("emitted_at_ms") or archive_emitted_at_ms)
    delay_ms = max(archive_emitted_at_ms - emitted_at_ms, 0)
    return {
        "similarity": similarity,
        "changed": changed,
        "delay_ms": delay_ms,
    }
