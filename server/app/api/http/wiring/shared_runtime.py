"""HTTP 런타임 공용 의존성 조립."""

from __future__ import annotations

import logging
from dataclasses import replace
from functools import lru_cache

from server.app.core.audio_source_policy import (
    AudioSourcePolicy,
    resolve_audio_source_policy,
)
from server.app.core.ai_service_profiles import (
    resolve_analyzer_service_profile,
    resolve_live_event_corrector_service_profile,
    resolve_report_refiner_service_profile,
    resolve_topic_summarizer_service_profile,
)
from server.app.core.media_service_profiles import (
    resolve_audio_preprocessor_profile,
    resolve_speaker_diarizer_profile,
    resolve_speech_to_text_profile,
)
from server.app.core.config import settings
from server.app.core.runtime_readiness import (
    finalize_runtime_readiness,
    mark_source_failed,
    mark_source_pending,
    mark_source_ready,
)
from server.app.api.http.wiring.persistence import (
    get_event_repository,
    get_transaction_manager,
    get_utterance_repository,
)
from server.app.domain.shared.enums import AudioSource, EventType
from server.app.services.analysis.analyzers.analyzer_factory import create_meeting_analyzer
from server.app.services.analysis.correction.live_event_correction_service import (
    AsyncLiveEventCorrectionService,
    NoOpLiveEventCorrectionService,
)
from server.app.services.analysis.event_type_policy import (
    filter_insight_event_type_values,
)
from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.audio.filters.audio_content_gate import (
    AudioContentGate,
    AudioContentGateProfile,
)
from server.app.services.audio.filters.transcription_guard import (
    TranscriptionGuard,
    TranscriptionGuardConfig,
)
from server.app.services.audio.pipeline.audio_pipeline_service import AudioPipelineService
from server.app.services.audio.preprocessing.audio_preprocessor_factory import (
    create_audio_preprocessor,
)
from server.app.services.audio.segmentation.silero_vad_segmenter import (
    SileroValidatedSpeechSegmenter,
    SileroVadValidatorConfig,
)
from server.app.services.audio.segmentation.speech_segmenter import (
    SpeechSegmenter,
    VadSegmenterConfig,
    VadSpeechSegmenter,
)
from server.app.services.audio.stt.speech_to_text_factory import (
    SpeechToTextBuildOptions,
    create_speech_to_text_service_from_options,
)
from server.app.services.diarization.speaker_diarizer_factory import (
    create_speaker_diarizer,
)
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.observability.runtime_monitor_service import (
    RuntimeMonitorService,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerEventProjectionService,
)
from server.app.services.reports.refinement.report_refiner_factory import (
    create_report_refiner,
)
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)
from server.app.services.sessions.topic_summarizer import (
    LLMTopicSummarizer,
    NoOpTopicSummarizer,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_runtime_monitor_service() -> RuntimeMonitorService:
    """런타임 운영 지표 수집기를 반환한다."""

    return RuntimeMonitorService()


def preload_runtime_services() -> None:
    """애플리케이션 시작 시 핵심 런타임 서비스를 미리 로드한다."""

    if not settings.stt_preload_on_startup:
        finalize_runtime_readiness()
        return None

    sources = [AudioSource.MIC.value]
    if settings.stt_backend_system_audio:
        sources.append(AudioSource.SYSTEM_AUDIO.value)

    for source in sources:
        profile = resolve_speech_to_text_profile(_resolve_stt_settings_for_source(source))
        mark_source_pending(
            source,
            backend=profile.backend_name,
            shared_instance=profile.shared_instance,
        )
        service = _create_speech_to_text_service(source)
        preload = getattr(service, "preload", None)
        if callable(preload):
            try:
                preload()
                mark_source_ready(source)
            except Exception:
                mark_source_failed(source, "preload_failed")
                logger.exception(
                    "STT preload 실패. source=%s 런타임 lazy-load로 계속 진행합니다.",
                    source,
                )

    finalize_runtime_readiness()
    return None


def _build_audio_pipeline_service(source: str) -> AudioPipelineService:
    source_policy = resolve_audio_source_policy(source, settings)
    event_repository = get_event_repository()
    return AudioPipelineService(
        segmenter=_build_audio_segmenter(source_policy),
        speech_to_text_service=_get_speech_to_text_service(source),
        analyzer_service=_get_shared_analyzer(),
        utterance_repository=get_utterance_repository(),
        event_service=MeetingEventService(event_repository),
        transcription_guard=_build_transcription_guard(source_policy),
        content_gate=_build_audio_content_gate(source_policy),
        live_event_corrector=_get_shared_live_event_corrector(),
        transaction_manager=get_transaction_manager(),
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
        runtime_monitor_service=get_runtime_monitor_service(),
    )


@lru_cache(maxsize=1)
def _get_shared_analyzer():
    profile = resolve_analyzer_service_profile(settings)
    return create_meeting_analyzer(
        backend_name=profile.backend_name,
        rules_config_path=str(settings.analysis_rules_config_path),
        llm_provider_backend=profile.completion_client.backend_name,
        llm_model=profile.completion_client.model,
        llm_base_url=profile.completion_client.base_url,
        llm_api_key=profile.completion_client.api_key,
        llm_timeout_seconds=profile.completion_client.timeout_seconds,
        analyzer_chain=profile.analyzer_stages,
    )


@lru_cache(maxsize=4)
def _get_shared_speech_to_text_service(source: str):
    return _create_speech_to_text_service(source)


def _get_speech_to_text_service(source: str):
    profile = resolve_speech_to_text_profile(_resolve_stt_settings_for_source(source))
    if profile.shared_instance:
        return _get_shared_speech_to_text_service(source)
    return _create_speech_to_text_service(source)


def _create_speech_to_text_service(source: str):
    source_settings = _resolve_stt_settings_for_source(source)
    profile = resolve_speech_to_text_profile(source_settings)
    logger.info(
        "STT 서비스 생성: source=%s backend=%s shared_instance=%s",
        source,
        profile.backend_name,
        profile.shared_instance,
    )
    return create_speech_to_text_service_from_options(_build_stt_build_options(profile))


def _build_stt_build_options(profile) -> SpeechToTextBuildOptions:
    """STT profile을 팩토리 옵션 객체로 변환한다."""

    return SpeechToTextBuildOptions(
        backend_name=profile.backend_name,
        model_id=profile.model_id,
        model_path=profile.model_path,
        base_model_id=profile.base_model_id,
        installation_path=profile.installation_path,
        encoder_model_path=profile.encoder_model_path,
        decoder_model_path=profile.decoder_model_path,
        encoder_rai_path=profile.encoder_rai_path,
        base_url=profile.base_url,
        api_key=profile.api_key,
        timeout_seconds=profile.timeout_seconds,
        language=profile.language,
        initial_prompt=profile.initial_prompt,
        device=profile.device,
        compute_type=profile.compute_type,
        cpu_threads=profile.cpu_threads,
        beam_size=profile.beam_size,
        sample_rate_hz=profile.sample_rate_hz,
        sample_width_bytes=profile.sample_width_bytes,
        channels=profile.channels,
        silence_rms_threshold=profile.silence_rms_threshold,
        partial_buffer_ms=profile.partial_buffer_ms,
        partial_emit_interval_ms=profile.partial_emit_interval_ms,
        partial_min_rms_threshold=profile.partial_min_rms_threshold,
        partial_agreement_window=profile.partial_agreement_window,
        partial_agreement_min_count=profile.partial_agreement_min_count,
        partial_min_stable_chars=profile.partial_min_stable_chars,
        partial_min_growth_chars=profile.partial_min_growth_chars,
        partial_backtrack_tolerance_chars=profile.partial_backtrack_tolerance_chars,
        partial_commit_min_chars_without_boundary=profile.partial_commit_min_chars_without_boundary,
        partial_backend_name=profile.partial_backend_name,
        partial_model_id=profile.partial_model_id,
        partial_model_path=profile.partial_model_path,
        partial_device=profile.partial_device,
        partial_compute_type=profile.partial_compute_type,
        partial_cpu_threads=profile.partial_cpu_threads,
        partial_beam_size=profile.partial_beam_size,
        final_backend_name=profile.final_backend_name,
        final_model_id=profile.final_model_id,
        final_model_path=profile.final_model_path,
        final_device=profile.final_device,
        final_compute_type=profile.final_compute_type,
        final_cpu_threads=profile.final_cpu_threads,
        final_beam_size=profile.final_beam_size,
    )


@lru_cache(maxsize=1)
def _get_shared_audio_preprocessor():
    profile = resolve_audio_preprocessor_profile(settings)
    return create_audio_preprocessor(
        profile.backend_name,
        model_path=profile.model_path,
        atten_lim_db=profile.atten_lim_db,
    )


@lru_cache(maxsize=1)
def _get_shared_speaker_diarizer():
    profile = resolve_speaker_diarizer_profile(settings)
    return create_speaker_diarizer(
        profile.backend_name,
        model_id=profile.model_id,
        auth_token=profile.auth_token,
        device=profile.device,
        default_speaker_label=profile.default_speaker_label,
        worker_python_executable=profile.worker_python_executable,
        worker_script_path=profile.worker_script_path,
        worker_timeout_seconds=profile.worker_timeout_seconds,
    )


@lru_cache(maxsize=1)
def _get_shared_audio_postprocessing_service():
    source_policy = resolve_audio_source_policy(AudioSource.FILE.value, settings)
    return AudioPostprocessingService(
        audio_preprocessor=_get_shared_audio_preprocessor(),
        speaker_diarizer=_get_shared_speaker_diarizer(),
        speech_to_text_service=_create_speech_to_text_service(AudioSource.FILE.value),
        transcription_guard=_build_transcription_guard(source_policy),
        expected_sample_rate_hz=settings.stt_sample_rate_hz,
        expected_sample_width_bytes=settings.stt_sample_width_bytes,
        expected_channels=settings.stt_channels,
    )


@lru_cache(maxsize=1)
def _get_shared_speaker_event_projection_service():
    return SpeakerEventProjectionService(
        analyzer=_get_shared_analyzer(),
    )


@lru_cache(maxsize=1)
def _get_shared_report_refiner():
    profile = resolve_report_refiner_service_profile(settings)
    if profile.backend_name == "noop":
        return StructuredMarkdownReportRefiner()

    backend_name = profile.backend_name
    if backend_name == "llm":
        backend_name = profile.completion_client.backend_name

    return create_report_refiner(
        backend_name=backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )


@lru_cache(maxsize=1)
def _get_shared_topic_summarizer():
    profile = resolve_topic_summarizer_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpTopicSummarizer()

    completion_client = create_llm_completion_client(
        backend_name=profile.completion_client.backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return LLMTopicSummarizer(completion_client)


@lru_cache(maxsize=1)
def _get_shared_live_event_corrector():
    profile = resolve_live_event_corrector_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpLiveEventCorrectionService()

    target_event_types = tuple(
        EventType(event_type)
        for event_type in filter_insight_event_type_values(profile.target_event_types)
    )
    analyzer = create_meeting_analyzer(
        backend_name="llm",
        rules_config_path=str(settings.analysis_rules_config_path),
        llm_provider_backend=profile.completion_client.backend_name,
        llm_model=profile.completion_client.model,
        llm_base_url=profile.completion_client.base_url,
        llm_api_key=profile.completion_client.api_key,
        llm_timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return AsyncLiveEventCorrectionService(
        analyzer=analyzer,
        event_service=MeetingEventService(get_event_repository()),
        transaction_manager=get_transaction_manager(),
        target_event_types=target_event_types,
        min_utterance_confidence=profile.min_utterance_confidence,
        min_text_length=profile.min_text_length,
        max_workers=profile.max_workers,
    )


def _build_audio_segmenter(source_policy: AudioSourcePolicy):
    segmenter = SpeechSegmenter()
    if source_policy.use_vad:
        segmenter = VadSpeechSegmenter(
            VadSegmenterConfig(
                sample_rate_hz=settings.stt_sample_rate_hz,
                sample_width_bytes=settings.stt_sample_width_bytes,
                channels=settings.stt_channels,
                frame_duration_ms=settings.vad_frame_duration_ms,
                pre_roll_ms=settings.vad_pre_roll_ms,
                early_post_roll_ms=source_policy.vad_early_post_roll_ms,
                post_roll_ms=source_policy.vad_post_roll_ms,
                min_speech_ms=source_policy.vad_min_speech_ms,
                max_segment_ms=source_policy.vad_max_segment_ms,
                min_activation_frames=source_policy.vad_min_activation_frames,
                rms_threshold=source_policy.vad_rms_threshold,
                adaptive_noise_floor_alpha=settings.vad_adaptive_noise_floor_alpha,
                adaptive_threshold_multiplier=source_policy.vad_adaptive_threshold_multiplier,
                active_threshold_ratio=source_policy.vad_active_threshold_ratio,
                min_voiced_ratio=source_policy.vad_min_voiced_ratio,
            )
        )
    if source_policy.silero_vad_enabled:
        segmenter = SileroValidatedSpeechSegmenter(
            base_segmenter=segmenter,
            config=SileroVadValidatorConfig(
                sample_rate_hz=settings.stt_sample_rate_hz,
                sample_width_bytes=settings.stt_sample_width_bytes,
                channels=settings.stt_channels,
                threshold=settings.silero_vad_threshold,
                min_speech_duration_ms=settings.silero_vad_min_speech_ms,
            ),
        )
    return segmenter


def _build_audio_content_gate(source_policy: AudioSourcePolicy) -> AudioContentGate:
    return AudioContentGate(
        AudioContentGateProfile(
            enabled=source_policy.content_gate_enabled,
            sample_rate_hz=settings.stt_sample_rate_hz,
            sample_width_bytes=settings.stt_sample_width_bytes,
            channels=settings.stt_channels,
            min_rms=source_policy.content_gate_min_rms,
            min_speech_band_ratio=source_policy.content_gate_min_speech_band_ratio,
            min_spectral_flatness=source_policy.content_gate_min_spectral_flatness,
            min_zero_crossing_rate=source_policy.content_gate_min_zero_crossing_rate,
        )
    )


def _build_transcription_guard(source_policy: AudioSourcePolicy) -> TranscriptionGuard:
    config = TranscriptionGuardConfig.with_patterns_from_path(
        settings.transcription_guard_config_path,
        min_confidence=source_policy.guard_min_confidence,
        short_text_min_confidence=source_policy.guard_short_text_min_confidence,
        min_compact_length=settings.stt_min_compact_length,
        max_repeat_ratio=source_policy.guard_max_repeat_ratio,
        max_consecutive_repeat=source_policy.guard_max_consecutive_repeat,
        min_repetition_tokens=source_policy.guard_min_repetition_tokens,
        expected_language=settings.stt_language,
        language_consistency_enabled=source_policy.guard_language_consistency_enabled,
        language_consistency_max_confidence=source_policy.guard_language_consistency_max_confidence,
        min_target_script_ratio=source_policy.guard_min_target_script_ratio,
        min_letter_ratio=source_policy.guard_min_letter_ratio,
        max_no_speech_prob=source_policy.guard_max_no_speech_prob,
    )
    if not source_policy.guard_blocked_phrases_enabled:
        config = TranscriptionGuardConfig(
            min_confidence=config.min_confidence,
            short_text_min_confidence=config.short_text_min_confidence,
            min_compact_length=config.min_compact_length,
            max_repeat_ratio=config.max_repeat_ratio,
            max_consecutive_repeat=config.max_consecutive_repeat,
            min_repetition_tokens=config.min_repetition_tokens,
            boundary_terms=config.boundary_terms,
            blocked_phrases=(),
            blocked_phrase_max_confidence=config.blocked_phrase_max_confidence,
            token_split_pattern=config.token_split_pattern,
            expected_language=config.expected_language,
            language_consistency_enabled=config.language_consistency_enabled,
            language_consistency_max_confidence=config.language_consistency_max_confidence,
            min_target_script_ratio=config.min_target_script_ratio,
            min_letter_ratio=config.min_letter_ratio,
            max_no_speech_prob=config.max_no_speech_prob,
        )
    return TranscriptionGuard(config)


def _resolve_stt_settings_for_source(source: str):
    if source in (AudioSource.SYSTEM_AUDIO.value, AudioSource.MIC_AND_AUDIO.value) and settings.stt_backend_system_audio:
        return replace(settings, stt_backend=settings.stt_backend_system_audio)
    return settings
