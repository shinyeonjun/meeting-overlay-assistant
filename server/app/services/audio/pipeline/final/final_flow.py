"""Final lane 공개 API를 한곳에서 다시 내보낸다.

실시간 오디오 파이프라인의 final 처리는 monitoring, persistence,
segment processing helper로 나뉘어 있다. 상위 서비스 입장에서는 helper
구조를 몰라도 되도록, final lane에서 외부에 노출할 함수만 이 모듈에서
안정적으로 재수출한다.
"""
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
