"""오디오 런타임 조립 보조 함수."""

from __future__ import annotations

from dataclasses import replace

from server.app.domain.shared.enums import AudioSource
from server.app.services.audio.filters.audio_content_gate import (
    AudioContentGate,
    AudioContentGateProfile,
)
from server.app.services.audio.filters.transcription_guard import (
    TranscriptionGuard,
    TranscriptionGuardConfig,
)
from server.app.services.audio.pipeline.audio_pipeline_service import AudioPipelineService
from server.app.services.audio.segmentation.silero_vad_segmenter import (
    SileroValidatedSpeechSegmenter,
    SileroVadValidatorConfig,
)
from server.app.services.audio.segmentation.speech_segmenter import (
    SpeechSegmenter,
    VadSegmenterConfig,
    VadSpeechSegmenter,
)
from server.app.services.audio.stt.placeholder_speech_to_text_service import (
    PlaceholderSpeechToTextService,
)
from server.app.services.audio.stt.speech_to_text_factory import SpeechToTextBuildOptions
from server.app.services.events.meeting_event_service import MeetingEventService


def preload_runtime_services(
    *,
    settings,
    logger,
    resolve_speech_to_text_profile,
    resolve_stt_settings_for_source,
    mark_source_pending,
    mark_source_ready,
    mark_source_failed,
    finalize_runtime_readiness,
    create_speech_to_text_service,
) -> None:
    """애플리케이션 시작 시 핵심 STT 서비스를 preload한다."""

    if not settings.stt_preload_on_startup:
        finalize_runtime_readiness()
        return None

    sources = [AudioSource.MIC.value]
    if settings.stt_backend_system_audio:
        sources.append(AudioSource.SYSTEM_AUDIO.value)

    for source in sources:
        profile = resolve_speech_to_text_profile(resolve_stt_settings_for_source(source))
        mark_source_pending(
            source,
            backend=profile.backend_name,
            shared_instance=profile.shared_instance,
        )
        service = create_speech_to_text_service(source)
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


def create_speech_to_text_service(
    *,
    source: str,
    settings,
    logger,
    resolve_speech_to_text_profile,
    resolve_stt_settings_for_source,
    build_stt_build_options,
    create_speech_to_text_service_from_options,
):
    """입력 소스에 맞는 STT 서비스를 생성한다."""

    source_settings = resolve_stt_settings_for_source(source)
    profile = resolve_speech_to_text_profile(source_settings)
    logger.info(
        "STT 서비스 생성: source=%s backend=%s shared_instance=%s",
        source,
        profile.backend_name,
        profile.shared_instance,
    )
    return create_speech_to_text_service_from_options(build_stt_build_options(profile))


def build_stt_build_options(profile) -> SpeechToTextBuildOptions:
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
) -> AudioPipelineService:
    """입력 소스별 오디오 파이프라인 서비스를 조립한다."""

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
) -> AudioPipelineService:
    """텍스트 입력용 오디오 파이프라인 서비스를 조립한다."""

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
    )


def build_audio_segmenter(*, source_policy, settings):
    """오디오 소스 정책에 맞는 segmenter를 조립한다."""

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


def build_audio_content_gate(*, source_policy, settings) -> AudioContentGate:
    """오디오 content gate를 조립한다."""

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


def build_transcription_guard(*, source_policy, settings) -> TranscriptionGuard:
    """입력 소스 정책에 맞는 transcription guard를 조립한다."""

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


def resolve_stt_settings_for_source(source: str, *, settings):
    """입력 소스에 따라 STT 설정 override를 적용한다."""

    if source in (AudioSource.SYSTEM_AUDIO.value, AudioSource.MIC_AND_AUDIO.value) and settings.stt_backend_system_audio:
        return replace(settings, stt_backend=settings.stt_backend_system_audio)
    return settings
