"""오디오 영역의 final flow 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.pipeline.final.helpers.monitoring import (
    apply_preview_backpressure,
    record_alignment_status,
    record_chunk_processed,
    record_processing_error,
    resolve_backend_name,
    resolve_live_final_delay_threshold_ms,
    should_emit_live_final,
    should_keep_short_final,
)
from server.app.services.audio.pipeline.final.helpers.persistence import (
    consume_segment_binding_for_final,
    save_final_utterance_and_events,
    should_skip_duplicate_transcription,
)
from server.app.services.audio.pipeline.final.helpers.segment_processing import (
    is_rejected_transcription,
    iter_processable_segments,
    log_transcription_rejection,
    process_segments,
    transcribe_segment,
)

__all__ = [
    "apply_preview_backpressure",
    "consume_segment_binding_for_final",
    "is_rejected_transcription",
    "iter_processable_segments",
    "log_transcription_rejection",
    "process_segments",
    "record_alignment_status",
    "record_chunk_processed",
    "record_processing_error",
    "resolve_backend_name",
    "resolve_live_final_delay_threshold_ms",
    "save_final_utterance_and_events",
    "should_emit_live_final",
    "should_keep_short_final",
    "should_skip_duplicate_transcription",
    "transcribe_segment",
]
