"""런타임/STT shared provider."""

from __future__ import annotations

from dataclasses import replace
import logging
from functools import lru_cache

from server.app.api.http.wiring import audio_runtime, service_builders
from server.app.core.config import settings
from server.app.core.media_service_profiles import resolve_speech_to_text_profile
from server.app.core.runtime_readiness import (
    finalize_runtime_readiness,
    mark_source_failed,
    mark_source_pending,
    mark_source_ready,
)
from server.app.services.audio.stt.speech_to_text_factory import (
    create_speech_to_text_service_from_options,
)


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_runtime_monitor_service():
    """공용 runtime monitor singleton을 반환한다."""

    return service_builders.build_runtime_monitor_service()


def preload_runtime_services() -> None:
    """애플리케이션 시작 시 공용 STT 서비스를 preload한다."""

    return audio_runtime.preload_runtime_services(
        settings=settings,
        logger=logger,
        resolve_speech_to_text_profile=resolve_speech_to_text_profile,
        resolve_stt_settings_for_source=resolve_stt_settings_for_source,
        mark_source_pending=mark_source_pending,
        mark_source_ready=mark_source_ready,
        mark_source_failed=mark_source_failed,
        finalize_runtime_readiness=finalize_runtime_readiness,
        create_speech_to_text_service=create_speech_to_text_service,
    )


def resolve_stt_settings_for_source(source: str):
    """입력 소스별 STT 설정 override를 적용한다."""

    return audio_runtime.resolve_stt_settings_for_source(
        source,
        settings=settings,
    )


def build_stt_build_options(profile):
    """STT profile을 factory 입력 옵션으로 변환한다."""

    return audio_runtime.build_stt_build_options(profile)


def create_speech_to_text_service(source: str):
    """공용 설정을 사용한 STT 서비스를 생성한다."""

    return audio_runtime.create_speech_to_text_service(
        source=source,
        settings=settings,
        logger=logger,
        resolve_speech_to_text_profile=resolve_speech_to_text_profile,
        resolve_stt_settings_for_source=resolve_stt_settings_for_source,
        build_stt_build_options=build_stt_build_options,
        create_speech_to_text_service_from_options=create_speech_to_text_service_from_options,
    )


def create_postprocessing_speech_to_text_service(source: str = "file"):
    """노트 후처리 전용 STT 서비스를 생성한다."""

    source_settings = resolve_stt_settings_for_source(source)
    note_settings = replace(
        source_settings,
        stt_backend="faster_whisper",
        stt_model_id=settings.note_transcript_stt_model_id,
        stt_model_path=settings.note_transcript_stt_model_path,
    )
    profile = resolve_speech_to_text_profile(note_settings)
    overridden_profile = replace(
        profile,
        model_id=settings.note_transcript_stt_model_id,
        model_path=settings.note_transcript_stt_model_path,
        beam_size=settings.note_transcript_stt_beam_size,
    )
    logger.info(
        "노트 후처리 STT 서비스 생성: source=%s backend=%s model=%s beam_size=%s",
        source,
        overridden_profile.backend_name,
        overridden_profile.model_id,
        overridden_profile.beam_size,
    )
    return create_speech_to_text_service_from_options(
        build_stt_build_options(overridden_profile)
    )


@lru_cache(maxsize=4)
def get_shared_speech_to_text_service(source: str):
    """shared_instance 소스의 STT singleton을 반환한다."""

    return create_speech_to_text_service(source)


def get_speech_to_text_service(source: str):
    """소스 설정에 맞는 STT 서비스를 반환한다."""

    profile = resolve_speech_to_text_profile(resolve_stt_settings_for_source(source))
    if profile.shared_instance:
        return get_shared_speech_to_text_service(source)
    return create_speech_to_text_service(source)
