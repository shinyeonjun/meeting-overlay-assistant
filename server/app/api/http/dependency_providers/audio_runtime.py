"""HTTP 계층에서 공통 관련 audio runtime 구성을 담당한다."""
from __future__ import annotations

import logging

from server.app.api.http.wiring import audio_runtime, runtime_streaming, shared_services
from server.app.api.http.wiring.persistence import (
    get_event_repository,
    get_transaction_manager,
    get_utterance_repository,
)
from server.app.core.audio_source_policy import resolve_audio_source_policy


def get_runtime_monitor_service():
    """공용 runtime monitor 서비스를 반환한다."""

    return shared_services.get_runtime_monitor_service()


def build_live_stream_service(*, settings):
    """live stream 서비스를 조립한다."""

    return runtime_streaming.build_live_stream_service(
        settings=settings,
        runtime_monitor_service=get_runtime_monitor_service(),
    )


def build_audio_pipeline_service_for_source(source: str):
    """입력 소스별 오디오 pipeline 서비스를 조립한다."""

    return shared_services.build_audio_pipeline_service(source)


def build_text_input_pipeline_service(*, settings, analyzer_service):
    """텍스트 입력용 pipeline 서비스를 조립한다."""

    return audio_runtime.build_text_input_pipeline_service(
        settings=settings,
        resolve_audio_source_policy=resolve_audio_source_policy,
        analyzer_service=analyzer_service,
        utterance_repository=get_utterance_repository(),
        event_repository=get_event_repository(),
        transaction_manager=get_transaction_manager(),
        runtime_monitor_service=get_runtime_monitor_service(),
    )


def preload_runtime_services(
    *,
    settings,
    logger: logging.Logger,
    resolve_speech_to_text_profile,
    resolve_stt_settings_for_source,
    mark_source_pending,
    mark_source_ready,
    mark_source_failed,
    finalize_runtime_readiness,
    create_speech_to_text_service,
) -> None:
    """runtime STT 서비스를 preload한다."""

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


def create_speech_to_text_service(
    *,
    source: str,
    settings,
    logger: logging.Logger,
    resolve_speech_to_text_profile,
    resolve_stt_settings_for_source,
    build_stt_build_options,
    create_speech_to_text_service_from_options,
):
    """입력 소스와 설정에 맞는 STT 서비스를 생성한다."""

    return audio_runtime.create_speech_to_text_service(
        source=source,
        settings=settings,
        logger=logger,
        resolve_speech_to_text_profile=resolve_speech_to_text_profile,
        resolve_stt_settings_for_source=resolve_stt_settings_for_source,
        build_stt_build_options=build_stt_build_options,
        create_speech_to_text_service_from_options=create_speech_to_text_service_from_options,
    )


def build_stt_build_options(profile):
    """STT profile을 build options로 변환한다."""

    return audio_runtime.build_stt_build_options(profile)


def build_audio_segmenter(*, source_policy, settings):
    """오디오 segmenter를 조립한다."""

    return audio_runtime.build_audio_segmenter(
        source_policy=source_policy,
        settings=settings,
    )


def build_audio_content_gate(*, source_policy, settings):
    """audio content gate를 조립한다."""

    return audio_runtime.build_audio_content_gate(
        source_policy=source_policy,
        settings=settings,
    )


def build_transcription_guard(*, source_policy, settings):
    """transcription guard를 조립한다."""

    return audio_runtime.build_transcription_guard(
        source_policy=source_policy,
        settings=settings,
    )


def resolve_stt_settings_for_source(source: str, *, settings):
    """입력 소스별 STT 설정 override를 적용한다."""

    return audio_runtime.resolve_stt_settings_for_source(
        source,
        settings=settings,
    )
