"""AudioPipelineService 초기화 helper."""

from __future__ import annotations

from server.app.services.analysis.correction.live_event_correction_service import (
    NoOpLiveEventCorrectionService,
)
from server.app.services.live_questions import NoOpLiveQuestionDispatchService
from server.app.services.audio.pipeline.orchestrators.helpers.runtime_setup import (
    initialize_runtime_lanes,
)


def configure_audio_pipeline_service(
    service,
    *,
    segmenter,
    speech_to_text_service,
    analyzer_service,
    utterance_repository,
    event_service,
    transcription_guard,
    content_gate,
    live_event_corrector,
    live_question_dispatcher,
    transaction_manager,
    duplicate_window_ms: int,
    duplicate_similarity_threshold: float,
    duplicate_max_confidence: float,
    preview_min_compact_length: int,
    preview_backpressure_queue_delay_ms: int,
    preview_backpressure_hold_chunks: int,
    segment_grace_match_max_gap_ms: int,
    live_final_emit_max_delay_ms: int,
    live_final_initial_grace_segments: int,
    live_final_initial_grace_delay_ms: int,
    final_short_text_max_compact_length: int,
    final_short_text_min_confidence: float,
    runtime_monitor_service,
) -> None:
    """AudioPipelineService 인스턴스 필드와 runtime lane을 초기화한다."""

    service._speech_to_text_service = speech_to_text_service
    service._analyzer_service = analyzer_service
    service._utterance_repository = utterance_repository
    service._event_service = event_service
    service._transcription_guard = transcription_guard
    service._content_gate = content_gate
    service._live_event_corrector = live_event_corrector or NoOpLiveEventCorrectionService()
    service._live_question_dispatcher = (
        live_question_dispatcher or NoOpLiveQuestionDispatchService()
    )
    service._live_question_analysis_enabled = bool(
        live_question_dispatcher
        and not isinstance(live_question_dispatcher, NoOpLiveQuestionDispatchService)
    )
    service._transaction_manager = transaction_manager
    service._duplicate_window_ms = duplicate_window_ms
    service._duplicate_similarity_threshold = duplicate_similarity_threshold
    service._duplicate_max_confidence = duplicate_max_confidence
    service._preview_min_compact_length = preview_min_compact_length
    service._preview_backpressure_queue_delay_ms = preview_backpressure_queue_delay_ms
    service._preview_backpressure_hold_chunks = preview_backpressure_hold_chunks
    service._segment_grace_match_max_gap_ms = segment_grace_match_max_gap_ms
    service._live_final_emit_max_delay_ms = live_final_emit_max_delay_ms
    service._live_final_initial_grace_segments = live_final_initial_grace_segments
    service._live_final_initial_grace_delay_ms = live_final_initial_grace_delay_ms
    service._final_short_text_max_compact_length = final_short_text_max_compact_length
    service._final_short_text_min_confidence = final_short_text_min_confidence
    service._runtime_monitor_service = runtime_monitor_service

    initialize_runtime_lanes(
        service,
        segmenter=segmenter,
        speech_to_text_service=speech_to_text_service,
        preview_backpressure_queue_delay_ms=preview_backpressure_queue_delay_ms,
        preview_backpressure_hold_chunks=preview_backpressure_hold_chunks,
        segment_grace_match_max_gap_ms=segment_grace_match_max_gap_ms,
    )
