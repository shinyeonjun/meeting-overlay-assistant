"""audio runtime pipeline builder."""

from __future__ import annotations

from server.app.domain.shared.enums import AudioSource
from server.app.services.audio.pipeline.orchestrators.audio_pipeline_service import (
    AudioPipelineService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegmenter
from server.app.services.audio.stt.placeholder_speech_to_text_service import (
    PlaceholderSpeechToTextService,
)
from server.app.services.events.meeting_event_service import MeetingEventService


def build_audio_pipeline_service(
    *,
    source: str,
    settings,
    resolve_audio_source_policy,
    speech_to_text_service,
    analyzer_service,
    utterance_repository,
    event_repository,
    transaction_manager,
    runtime_monitor_service,
    live_event_corrector,
    live_question_dispatcher,
    build_audio_segmenter,
    build_audio_content_gate,
    build_transcription_guard,
) -> AudioPipelineService:
    """입력 소스별 오디오 pipeline 서비스를 조립한다."""

    source_policy = resolve_audio_source_policy(source, settings)
    return AudioPipelineService(
        segmenter=build_audio_segmenter(source_policy=source_policy, settings=settings),
        speech_to_text_service=speech_to_text_service,
        analyzer_service=analyzer_service,
        utterance_repository=utterance_repository,
        event_service=MeetingEventService(event_repository),
        transcription_guard=build_transcription_guard(
            source_policy=source_policy,
            settings=settings,
        ),
        content_gate=build_audio_content_gate(
            source_policy=source_policy,
            settings=settings,
        ),
        live_event_corrector=live_event_corrector,
        live_question_dispatcher=live_question_dispatcher,
        transaction_manager=transaction_manager,
        duplicate_window_ms=source_policy.duplicate_window_ms,
        duplicate_similarity_threshold=source_policy.duplicate_similarity_threshold,
        duplicate_max_confidence=source_policy.duplicate_max_confidence,
        preview_min_compact_length=source_policy.preview_min_compact_length,
        preview_backpressure_queue_delay_ms=source_policy.preview_backpressure_queue_delay_ms,
        preview_backpressure_hold_chunks=source_policy.preview_backpressure_hold_chunks,
        segment_grace_match_max_gap_ms=source_policy.segment_grace_match_max_gap_ms,
        live_final_emit_max_delay_ms=source_policy.live_final_emit_max_delay_ms,
        live_final_initial_grace_segments=source_policy.live_final_initial_grace_segments,
        live_final_initial_grace_delay_ms=source_policy.live_final_initial_grace_delay_ms,
        final_short_text_max_compact_length=source_policy.final_short_text_max_compact_length,
        final_short_text_min_confidence=source_policy.final_short_text_min_confidence,
        runtime_monitor_service=runtime_monitor_service,
        persist_live_runtime_data=False,
    )


def build_text_input_pipeline_service(
    *,
    settings,
    resolve_audio_source_policy,
    analyzer_service,
    utterance_repository,
    event_repository,
    transaction_manager,
    runtime_monitor_service,
    build_transcription_guard,
) -> AudioPipelineService:
    """텍스트 입력용 placeholder pipeline을 조립한다."""

    source_policy = resolve_audio_source_policy(AudioSource.MIC.value, settings)
    return AudioPipelineService(
        segmenter=SpeechSegmenter(),
        speech_to_text_service=PlaceholderSpeechToTextService(),
        analyzer_service=analyzer_service,
        utterance_repository=utterance_repository,
        event_service=MeetingEventService(event_repository),
        transcription_guard=build_transcription_guard(
            source_policy=source_policy,
            settings=settings,
        ),
        transaction_manager=transaction_manager,
        runtime_monitor_service=runtime_monitor_service,
        persist_live_runtime_data=False,
    )
