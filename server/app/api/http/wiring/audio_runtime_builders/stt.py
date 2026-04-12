"""HTTP 계층에서 공통 관련 stt 구성을 담당한다."""
from __future__ import annotations

from dataclasses import replace

from server.app.domain.shared.enums import AudioSource
from server.app.services.audio.stt.speech_to_text_factory import SpeechToTextBuildOptions


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
    """STT profile을 factory build options로 변환한다."""

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


def resolve_stt_settings_for_source(source: str, *, settings):
    """입력 소스별 STT 설정 override를 적용한다."""

    if source in (AudioSource.SYSTEM_AUDIO.value, AudioSource.MIC_AND_AUDIO.value) and settings.stt_backend_system_audio:
        return replace(settings, stt_backend=settings.stt_backend_system_audio)
    return settings

