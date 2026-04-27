"""HTTP 계층에서 공통 관련 dependencies 구성을 담당한다."""
from __future__ import annotations

import logging
from functools import lru_cache

from server.app.api.http.dependency_providers import (
    get_auth_service,
    get_context_catalog_service,
    get_context_resolution_service,
    get_event_lifecycle_service,
    get_event_management_service,
    get_history_query_service,
    get_meeting_context_service,
    get_note_correction_job_service,
    get_participant_followup_service,
    get_participation_query_service,
    get_post_meeting_pipeline_recovery_service,
    get_post_meeting_pipeline_service,
    get_report_generation_job_service,
    get_report_knowledge_indexing_service,
    get_report_service,
    get_report_share_service,
    get_retrieval_query_service,
    get_session_post_processing_job_service,
    get_session_recovery_service,
    get_runtime_monitor_service as _get_runtime_monitor_service,
    get_session_finalization_service,
    get_session_overview_service,
    get_session_service,
)
from server.app.api.http.dependency_providers import audio_runtime as audio_runtime_dependencies
from server.app.api.http.wiring import shared_services
from server.app.api.http.wiring.live_question_queue import get_live_question_analysis_queue
from server.app.api.http.wiring.persistence import initialize_primary_persistence
from server.app.core.config import settings
from server.app.core.media_service_profiles import resolve_speech_to_text_profile
from server.app.core.runtime_readiness import (
    finalize_runtime_readiness,
    mark_source_failed,
    mark_source_pending,
    mark_source_ready,
)
from server.app.domain.shared.enums import AudioSource
from server.app.services.audio.stt.speech_to_text_factory import (
    create_speech_to_text_service_from_options,
)
from server.app.services.live_questions import LiveQuestionResultConsumer

logger = logging.getLogger(__name__)

# 테스트 코드가 기존 private getter 이름을 참조하므로 함수 이름은 유지하고
# 구현만 공용 provider 모듈로 위임한다.
_get_shared_analyzer = shared_services.get_shared_analyzer
_get_shared_live_analyzer = shared_services.get_shared_live_analyzer
_get_shared_post_processing_analyzer = shared_services.get_shared_post_processing_analyzer
_get_shared_report_analyzer = shared_services.get_shared_report_analyzer
_get_shared_audio_preprocessor = shared_services.get_shared_audio_preprocessor
_get_shared_speaker_diarizer = shared_services.get_shared_speaker_diarizer
_get_shared_audio_postprocessing_service = (
    shared_services.get_shared_audio_postprocessing_service
)
_get_shared_speaker_event_projection_service = (
    shared_services.get_shared_speaker_event_projection_service
)
_get_shared_topic_summarizer = shared_services.get_shared_topic_summarizer
_get_shared_live_event_corrector = shared_services.get_shared_live_event_corrector
_get_shared_live_question_dispatcher = shared_services.get_shared_live_question_dispatcher
_get_shared_live_question_state_store = shared_services.get_shared_live_question_state_store


def get_runtime_monitor_service():
    """공용 runtime monitor 서비스를 반환한다."""

    return _get_runtime_monitor_service()


@lru_cache(maxsize=1)
def get_live_stream_service():
    """실시간 스트림 서비스를 반환한다."""

    return audio_runtime_dependencies.build_live_stream_service(settings=settings)


@lru_cache(maxsize=1)
def get_live_question_result_consumer():
    """실시간 질문 결과 consumer를 반환한다."""

    queue = get_live_question_analysis_queue()
    if not settings.live_question_analysis_enabled or queue is None:
        return None
    return LiveQuestionResultConsumer(
        queue=queue,
        state_store=_get_shared_live_question_state_store(),
        live_stream_service=get_live_stream_service(),
        block_seconds=settings.live_question_stream_block_seconds,
    )


def get_audio_pipeline_service():
    """기본 mic 오디오 pipeline을 조립한다."""

    return _build_audio_pipeline_service(AudioSource.MIC.value)


def get_audio_pipeline_service_for_source(source: str):
    """입력 소스별 오디오 pipeline을 조립한다."""

    return _build_audio_pipeline_service(source)


def get_text_input_pipeline_service():
    """텍스트 입력용 pipeline을 조립한다."""

    return audio_runtime_dependencies.build_text_input_pipeline_service(
        settings=settings,
        analyzer_service=_get_shared_live_analyzer(),
    )


def preload_runtime_services() -> None:
    """애플리케이션 시작 시 공용 STT 서비스를 preload한다."""

    return audio_runtime_dependencies.preload_runtime_services(
        settings=settings,
        logger=logger,
        resolve_speech_to_text_profile=resolve_speech_to_text_profile,
        resolve_stt_settings_for_source=_resolve_stt_settings_for_source,
        mark_source_pending=mark_source_pending,
        mark_source_ready=mark_source_ready,
        mark_source_failed=mark_source_failed,
        finalize_runtime_readiness=finalize_runtime_readiness,
        create_speech_to_text_service=_create_speech_to_text_service,
    )


async def start_live_stream_service() -> None:
    """실시간 스트림 서비스를 시작한다."""

    await get_live_stream_service().start()
    consumer = get_live_question_result_consumer()
    if consumer is not None:
        await consumer.start()


async def shutdown_live_stream_service() -> None:
    """실시간 스트림 서비스와 컨텍스트를 정리한다."""

    consumer = get_live_question_result_consumer()
    if consumer is not None:
        await consumer.shutdown()
    service = get_live_stream_service()
    await service.shutdown()
    dispatcher = _get_shared_live_question_dispatcher()
    dispatcher.shutdown()
    get_live_stream_service.cache_clear()
    get_live_question_result_consumer.cache_clear()
    _get_shared_live_question_dispatcher.cache_clear()
    _get_shared_live_question_state_store.cache_clear()


def _build_audio_pipeline_service(source: str):
    """입력 소스별 오디오 pipeline을 구성한다."""

    return audio_runtime_dependencies.build_audio_pipeline_service_for_source(source)


@lru_cache(maxsize=4)
def _get_shared_speech_to_text_service(source: str):
    """source별 shared STT 인스턴스를 캐시한다."""

    return _create_speech_to_text_service(source)


def _get_speech_to_text_service(source: str):
    """source 설정에 맞는 STT 서비스를 반환한다."""

    profile = resolve_speech_to_text_profile(_resolve_stt_settings_for_source(source))
    if profile.shared_instance:
        return _get_shared_speech_to_text_service(source)
    return _create_speech_to_text_service(source)


def _create_speech_to_text_service(source: str):
    """현재 dependency 설정을 기준으로 STT 서비스를 생성한다."""

    return audio_runtime_dependencies.create_speech_to_text_service(
        source=source,
        settings=settings,
        logger=logger,
        resolve_speech_to_text_profile=resolve_speech_to_text_profile,
        resolve_stt_settings_for_source=_resolve_stt_settings_for_source,
        build_stt_build_options=_build_stt_build_options,
        create_speech_to_text_service_from_options=create_speech_to_text_service_from_options,
    )


def _build_stt_build_options(profile):
    """STT profile을 factory build options로 변환한다."""

    return audio_runtime_dependencies.build_stt_build_options(profile)


def _build_audio_segmenter(source_policy):
    """오디오 segmenter를 현재 설정으로 구성한다."""

    return audio_runtime_dependencies.build_audio_segmenter(
        source_policy=source_policy,
        settings=settings,
    )


def _build_audio_content_gate(source_policy):
    """audio content gate를 현재 설정으로 구성한다."""

    return audio_runtime_dependencies.build_audio_content_gate(
        source_policy=source_policy,
        settings=settings,
    )


def _build_transcription_guard(source_policy):
    """transcription guard를 현재 설정으로 구성한다."""

    return audio_runtime_dependencies.build_transcription_guard(
        source_policy=source_policy,
        settings=settings,
    )


def _resolve_stt_settings_for_source(source: str):
    """입력 소스별 STT 설정 override를 적용한다."""

    return audio_runtime_dependencies.resolve_stt_settings_for_source(
        source,
        settings=settings,
    )
