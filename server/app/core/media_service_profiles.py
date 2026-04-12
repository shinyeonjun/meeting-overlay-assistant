"""오디오 처리 서비스 프로파일 resolver."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.core.config import AppConfig
from server.app.core.media_service_profile_helpers import (
    build_audio_preprocessor_profile_kwargs,
    build_speaker_diarizer_profile_kwargs,
    build_speech_to_text_profile_kwargs,
    load_media_service_profiles,
)


@dataclass(frozen=True)
class SpeechToTextProfile:
    """STT 최종 설정."""

    backend_name: str
    model_id: str
    model_path: str | None
    base_model_id: str | None
    installation_path: str | None
    encoder_model_path: str | None
    decoder_model_path: str | None
    encoder_rai_path: str | None
    base_url: str
    api_key: str | None
    timeout_seconds: float
    language: str | None
    initial_prompt: str | None
    device: str
    compute_type: str
    cpu_threads: int
    beam_size: int
    sample_rate_hz: int
    sample_width_bytes: int
    channels: int
    silence_rms_threshold: float
    shared_instance: bool
    partial_buffer_ms: int
    partial_emit_interval_ms: int
    partial_min_rms_threshold: float
    partial_agreement_window: int
    partial_agreement_min_count: int
    partial_min_stable_chars: int
    partial_min_growth_chars: int
    partial_backtrack_tolerance_chars: int
    partial_commit_min_chars_without_boundary: int
    partial_backend_name: str | None
    partial_model_id: str | None
    partial_model_path: str | None
    partial_device: str | None
    partial_compute_type: str | None
    partial_cpu_threads: int | None
    partial_beam_size: int | None
    final_backend_name: str | None
    final_model_id: str | None
    final_model_path: str | None
    final_device: str | None
    final_compute_type: str | None
    final_cpu_threads: int | None
    final_beam_size: int | None


@dataclass(frozen=True)
class AudioPreprocessorProfile:
    """오디오 전처리기 최종 설정."""

    backend_name: str
    model_path: str | None
    atten_lim_db: float


@dataclass(frozen=True)
class SpeakerDiarizerProfile:
    """화자 분리기 최종 설정."""

    backend_name: str
    model_id: str
    auth_token: str | None
    device: str
    default_speaker_label: str
    worker_python_executable: str | None
    worker_script_path: str | None
    worker_timeout_seconds: float


def resolve_speech_to_text_profile(settings: AppConfig) -> SpeechToTextProfile:
    """STT 프로파일을 로드한다."""

    profiles = load_media_service_profiles(str(settings.media_service_profiles_config_path))
    profile = profiles.get("speech_to_text", {}).get(settings.stt_backend, {})
    return SpeechToTextProfile(
        **build_speech_to_text_profile_kwargs(
            settings=settings,
            profile=profile,
        )
    )


def resolve_audio_preprocessor_profile(settings: AppConfig) -> AudioPreprocessorProfile:
    """오디오 전처리기 프로파일을 로드한다."""

    profiles = load_media_service_profiles(str(settings.media_service_profiles_config_path))
    profile = profiles.get("audio_preprocessors", {}).get(settings.audio_preprocessor_backend, {})
    return AudioPreprocessorProfile(
        **build_audio_preprocessor_profile_kwargs(
            settings=settings,
            profile=profile,
        )
    )


def resolve_speaker_diarizer_profile(settings: AppConfig) -> SpeakerDiarizerProfile:
    """화자 분리기 프로파일을 로드한다."""

    profiles = load_media_service_profiles(str(settings.media_service_profiles_config_path))
    profile = profiles.get("speaker_diarizers", {}).get(settings.speaker_diarizer_backend, {})
    return SpeakerDiarizerProfile(
        **build_speaker_diarizer_profile_kwargs(
            settings=settings,
            profile=profile,
        )
    )
