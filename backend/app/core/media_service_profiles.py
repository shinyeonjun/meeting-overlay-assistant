"""오디오 처리 서비스 프로파일 resolver."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.core.config import AppConfig


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


@lru_cache(maxsize=1)
def _load_media_service_profiles(config_path: str) -> dict[str, Any]:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def resolve_speech_to_text_profile(settings: AppConfig) -> SpeechToTextProfile:
    """STT 프로파일을 로드한다."""

    profiles = _load_media_service_profiles(str(settings.media_service_profiles_config_path))
    profile = profiles.get("speech_to_text", {}).get(settings.stt_backend, {})

    return SpeechToTextProfile(
        backend_name=str(profile.get("backend_name", settings.stt_backend)),
        model_id=str(profile.get("model_id", settings.stt_model_id)),
        model_path=str(profile["model_path"]) if profile.get("model_path") else settings.stt_model_path,
        base_model_id=str(profile["base_model_id"]) if profile.get("base_model_id") else settings.stt_base_model_id,
        installation_path=str(profile["installation_path"]) if profile.get("installation_path") else settings.ryzen_ai_installation_path,
        encoder_model_path=str(profile["encoder_model_path"]) if profile.get("encoder_model_path") else settings.stt_encoder_model_path,
        decoder_model_path=str(profile["decoder_model_path"]) if profile.get("decoder_model_path") else settings.stt_decoder_model_path,
        encoder_rai_path=str(profile["encoder_rai_path"]) if profile.get("encoder_rai_path") else settings.stt_encoder_rai_path,
        base_url=str(profile.get("base_url", settings.stt_base_url)),
        api_key=str(profile["api_key"]) if profile.get("api_key") else settings.stt_api_key,
        timeout_seconds=float(profile.get("timeout_seconds", settings.stt_timeout_seconds)),
        language=str(profile["language"]) if profile.get("language") else settings.stt_language,
        initial_prompt=(
            str(profile["initial_prompt"])
            if profile.get("initial_prompt") is not None
            else settings.stt_initial_prompt
        ),
        device=str(profile.get("device", settings.stt_device)),
        compute_type=str(profile.get("compute_type", settings.stt_compute_type)),
        cpu_threads=int(profile.get("cpu_threads", settings.stt_cpu_threads)),
        beam_size=int(profile.get("beam_size", settings.stt_beam_size)),
        sample_rate_hz=int(profile.get("sample_rate_hz", settings.stt_sample_rate_hz)),
        sample_width_bytes=int(profile.get("sample_width_bytes", settings.stt_sample_width_bytes)),
        channels=int(profile.get("channels", settings.stt_channels)),
        silence_rms_threshold=float(profile.get("silence_rms_threshold", settings.stt_silence_rms_threshold)),
        shared_instance=bool(profile.get("shared_instance", True)),
        partial_buffer_ms=int(profile.get("partial_buffer_ms", settings.partial_buffer_ms)),
        partial_emit_interval_ms=int(
            profile.get("partial_emit_interval_ms", settings.partial_emit_interval_ms)
        ),
        partial_min_rms_threshold=float(
            profile.get("partial_min_rms_threshold", settings.partial_min_rms_threshold)
        ),
        partial_agreement_window=int(
            profile.get("partial_agreement_window", settings.partial_agreement_window)
        ),
        partial_agreement_min_count=int(
            profile.get("partial_agreement_min_count", settings.partial_agreement_min_count)
        ),
        partial_min_stable_chars=int(
            profile.get("partial_min_stable_chars", settings.partial_min_stable_chars)
        ),
        partial_min_growth_chars=int(
            profile.get("partial_min_growth_chars", settings.partial_min_growth_chars)
        ),
        partial_backtrack_tolerance_chars=int(
            profile.get(
                "partial_backtrack_tolerance_chars",
                settings.partial_backtrack_tolerance_chars,
            )
        ),
        partial_commit_min_chars_without_boundary=int(
            profile.get(
                "partial_commit_min_chars_without_boundary",
                settings.partial_commit_min_chars_without_boundary,
            )
        ),
        partial_backend_name=(
            str(profile["partial_backend_name"])
            if profile.get("partial_backend_name")
            else None
        ),
        partial_model_id=(
            str(profile["partial_model_id"])
            if profile.get("partial_model_id")
            else None
        ),
        partial_model_path=(
            str(profile["partial_model_path"])
            if profile.get("partial_model_path")
            else None
        ),
        partial_device=(
            str(profile["partial_device"])
            if profile.get("partial_device")
            else None
        ),
        partial_compute_type=(
            str(profile["partial_compute_type"])
            if profile.get("partial_compute_type")
            else None
        ),
        partial_cpu_threads=(
            int(profile["partial_cpu_threads"])
            if profile.get("partial_cpu_threads") is not None
            else None
        ),
        partial_beam_size=(
            int(profile["partial_beam_size"])
            if profile.get("partial_beam_size") is not None
            else None
        ),
        final_backend_name=(
            str(profile["final_backend_name"])
            if profile.get("final_backend_name")
            else None
        ),
        final_model_id=(
            str(profile["final_model_id"])
            if profile.get("final_model_id")
            else None
        ),
        final_model_path=(
            str(profile["final_model_path"])
            if profile.get("final_model_path")
            else settings.stt_model_path
        ),
        final_device=(
            str(profile["final_device"])
            if profile.get("final_device")
            else None
        ),
        final_compute_type=(
            str(profile["final_compute_type"])
            if profile.get("final_compute_type")
            else None
        ),
        final_cpu_threads=(
            int(profile["final_cpu_threads"])
            if profile.get("final_cpu_threads") is not None
            else None
        ),
        final_beam_size=(
            int(profile["final_beam_size"])
            if profile.get("final_beam_size") is not None
            else None
        ),
    )


def resolve_audio_preprocessor_profile(settings: AppConfig) -> AudioPreprocessorProfile:
    """오디오 전처리기 프로파일을 로드한다."""

    profiles = _load_media_service_profiles(str(settings.media_service_profiles_config_path))
    profile = profiles.get("audio_preprocessors", {}).get(settings.audio_preprocessor_backend, {})

    return AudioPreprocessorProfile(
        backend_name=str(profile.get("backend_name", settings.audio_preprocessor_backend)),
        model_path=str(profile["model_path"]) if profile.get("model_path") else settings.audio_preprocessor_model_path,
        atten_lim_db=float(profile.get("atten_lim_db", settings.audio_preprocessor_atten_lim_db)),
    )


def resolve_speaker_diarizer_profile(settings: AppConfig) -> SpeakerDiarizerProfile:
    """화자 분리기 프로파일을 로드한다."""

    profiles = _load_media_service_profiles(str(settings.media_service_profiles_config_path))
    profile = profiles.get("speaker_diarizers", {}).get(settings.speaker_diarizer_backend, {})

    return SpeakerDiarizerProfile(
        backend_name=str(profile.get("backend_name", settings.speaker_diarizer_backend)),
        model_id=str(profile.get("model_id", settings.speaker_diarizer_model_id)),
        auth_token=str(profile["auth_token"]) if profile.get("auth_token") else settings.speaker_diarizer_auth_token,
        device=str(profile.get("device", settings.speaker_diarizer_device)),
        default_speaker_label=str(profile.get("default_speaker_label", settings.speaker_diarizer_default_label)),
        worker_python_executable=(
            str(profile["worker_python_executable"])
            if profile.get("worker_python_executable")
            else settings.speaker_diarizer_worker_python
        ),
        worker_script_path=(
            str(profile["worker_script_path"])
            if profile.get("worker_script_path")
            else settings.speaker_diarizer_worker_script_path
        ),
        worker_timeout_seconds=float(profile.get("timeout_seconds", settings.speaker_diarizer_worker_timeout_seconds)),
    )
