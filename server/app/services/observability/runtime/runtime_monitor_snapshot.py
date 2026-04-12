"""런타임 관측성 스냅샷 계산기."""

from __future__ import annotations

from server.app.services.observability.runtime.metrics_helpers import utc_now_iso
from server.app.services.observability.runtime.snapshot_builders.audio_pipeline import (
    build_audio_pipeline_metrics,
)


def build_runtime_snapshot(
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
    session_id: str | None = None,
) -> dict[str, object]:
    """최근 런타임 기록을 API 응답용 스냅샷으로 축약한다."""

    if session_id:
        finals = [item for item in finals if item.get("session_id") == session_id]
        previews = [item for item in previews if item.get("session_id") == session_id]
        preview_cycles = [item for item in preview_cycles if item.get("session_id") == session_id]
        chunks = [item for item in chunks if item.get("session_id") == session_id]
        rejections = [item for item in rejections if item.get("session_id") == session_id]
        backpressure = [item for item in backpressure if item.get("session_id") == session_id]
        errors = []
        last_chunk_processed_at = None
        last_error_at = None
        last_error_message = None

    return {
        "generated_at": utc_now_iso(),
        "audio_pipeline": build_audio_pipeline_metrics(
            finals=finals,
            previews=previews,
            preview_cycles=preview_cycles,
            chunks=chunks,
            rejections=rejections,
            backpressure=backpressure,
            errors=errors,
            last_chunk_processed_at=last_chunk_processed_at,
            last_error_at=last_error_at,
            last_error_message=last_error_message,
        ),
    }
