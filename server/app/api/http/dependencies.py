"""API 의존성 조립 facade."""

from __future__ import annotations

import logging
from functools import lru_cache

from server.app.api.http.wiring import (
    audio_runtime,
    runtime_streaming,
    service_builders,
    shared_factories,
)
from server.app.api.http.wiring.persistence import (
    get_auth_repository,
    get_event_repository,
    get_knowledge_chunk_repository,
    get_knowledge_document_repository,
    initialize_primary_persistence,
    get_meeting_context_repository,
    get_participant_followup_repository,
    get_report_generation_job_repository,
    get_report_repository,
    get_report_share_repository,
    get_session_repository,
    get_transaction_manager,
    get_utterance_repository,
)
from server.app.core.ai_service_profiles import (
    resolve_analyzer_service_profile,
    resolve_live_event_corrector_service_profile,
    resolve_report_refiner_service_profile,
    resolve_topic_summarizer_service_profile,
)
from server.app.core.audio_source_policy import resolve_audio_source_policy
from server.app.core.config import ROOT_DIR, settings
from server.app.core.media_service_profiles import (
    resolve_audio_preprocessor_profile,
    resolve_speaker_diarizer_profile,
    resolve_speech_to_text_profile,
)
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

logger = logging.getLogger(__name__)


def get_auth_service():
    """인증 서비스를 조립한다."""

    return service_builders.build_auth_service(
        auth_repository=get_auth_repository(),
        session_ttl_hours=settings.auth_session_ttl_hours,
    )


def get_session_service():
    """세션 서비스를 조립한다."""

    return service_builders.build_session_service(
        session_repository=get_session_repository(),
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_meeting_context_service():
    """회의 맥락 서비스를 조립한다."""

    return service_builders.build_meeting_context_service(
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_context_catalog_service():
    """맥락 정본 catalog 서비스를 조립한다."""

    return service_builders.build_context_catalog_service(
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_context_resolution_service():
    """세션용 맥락 정합성 해결 서비스를 조립한다."""

    return service_builders.build_context_resolution_service(
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_history_query_service():
    """history 타임라인 조회 서비스를 조립한다."""

    return service_builders.build_history_query_service(
        session_service=get_session_service(),
        report_service=get_report_service(),
        context_resolution_service=get_context_resolution_service(),
        event_management_service=get_event_management_service(),
        retrieval_query_service=get_retrieval_query_service(),
    )


def get_participant_followup_service():
    """참여자 후속 작업 서비스를 조립한다."""

    return service_builders.build_participant_followup_service(
        participant_followup_repository=get_participant_followup_repository(),
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_participation_query_service():
    """참여자 상세 조회 서비스를 조립한다."""

    return service_builders.build_participation_query_service(
        participant_followup_repository=get_participant_followup_repository(),
        meeting_context_repository=get_meeting_context_repository(),
    )


@lru_cache(maxsize=1)
def get_runtime_monitor_service():
    """런타임 모니터 서비스를 반환한다."""

    return service_builders.build_runtime_monitor_service()


@lru_cache(maxsize=1)
def get_live_stream_service():
    """실시간 스트림 런타임 서비스를 반환한다."""

    return runtime_streaming.build_live_stream_service(settings=settings)


def get_session_finalization_service():
    """세션 종료 후속 서비스를 조립한다."""

    return service_builders.build_session_finalization_service(
        session_service=get_session_service(),
        report_generation_job_service=get_report_generation_job_service(),
        participant_followup_service=get_participant_followup_service(),
    )


def get_post_meeting_pipeline_service():
    """회의 종료 후 후처리 pipeline 서비스를 조립한다."""

    return service_builders.build_post_meeting_pipeline_service(
        session_service=get_session_service(),
        report_generation_job_service=get_report_generation_job_service(),
        participant_followup_service=get_participant_followup_service(),
    )


def get_audio_pipeline_service():
    """기본 마이크 오디오 파이프라인을 조립한다."""

    return _build_audio_pipeline_service(AudioSource.MIC.value)


def get_audio_pipeline_service_for_source(source: str):
    """입력 소스별 오디오 파이프라인을 조립한다."""

    return _build_audio_pipeline_service(source)


def get_text_input_pipeline_service():
    """텍스트 입력용 파이프라인을 조립한다."""

    return audio_runtime.build_text_input_pipeline_service(
        settings=settings,
        resolve_audio_source_policy=resolve_audio_source_policy,
        analyzer_service=_get_shared_analyzer(),
        utterance_repository=get_utterance_repository(),
        event_repository=get_event_repository(),
        transaction_manager=get_transaction_manager(),
        runtime_monitor_service=get_runtime_monitor_service(),
    )


def get_event_management_service():
    """이벤트 관리 서비스를 조립한다."""

    return service_builders.build_event_management_service(
        meeting_event_repository=get_event_repository(),
    )


def get_event_lifecycle_service():
    """이벤트 상태 전이 서비스를 조립한다."""

    return service_builders.build_event_lifecycle_service(
        meeting_event_repository=get_event_repository(),
    )


def get_report_service():
    """리포트 서비스를 조립한다."""

    return service_builders.build_report_service(
        event_repository=get_event_repository(),
        report_repository=get_report_repository(),
        audio_postprocessing_service=_get_shared_audio_postprocessing_service(),
        speaker_event_projection_service=_get_shared_speaker_event_projection_service(),
        report_refiner=_get_shared_report_refiner(),
    )


def get_report_generation_job_service():
    """리포트 생성 job 서비스를 조립한다."""

    return service_builders.build_report_generation_job_service(
        report_generation_job_repository=get_report_generation_job_repository(),
        report_service=get_report_service(),
        report_knowledge_indexing_service=get_report_knowledge_indexing_service(),
        output_dir=ROOT_DIR / "server" / "data" / "reports",
    )


def get_report_knowledge_indexing_service():
    """리포트 knowledge 인덱싱 서비스를 조립한다."""

    if settings.persistence_backend != "postgresql":
        return None

    embedding_service = service_builders.build_ollama_embedding_service(
        base_url=settings.retrieval_embedding_base_url,
        model=settings.retrieval_embedding_model,
        timeout_seconds=settings.retrieval_embedding_timeout_seconds,
    )
    return service_builders.build_report_knowledge_indexing_service(
        session_repository=get_session_repository(),
        knowledge_document_repository=get_knowledge_document_repository(),
        knowledge_chunk_repository=get_knowledge_chunk_repository(),
        embedding_service=embedding_service,
        chunk_target_chars=settings.retrieval_chunk_target_chars,
        chunk_overlap_chars=settings.retrieval_chunk_overlap_chars,
    )


def get_retrieval_query_service():
    """retrieval 검색 서비스를 조립한다."""

    if settings.persistence_backend != "postgresql":
        return None

    embedding_service = service_builders.build_ollama_embedding_service(
        base_url=settings.retrieval_embedding_base_url,
        model=settings.retrieval_embedding_model,
        timeout_seconds=settings.retrieval_embedding_timeout_seconds,
    )
    return service_builders.build_retrieval_query_service(
        knowledge_chunk_repository=get_knowledge_chunk_repository(),
        embedding_service=embedding_service,
        candidate_limit=settings.retrieval_search_candidate_limit,
    )


def get_report_share_service():
    """리포트 공유 서비스를 조립한다."""

    return service_builders.build_report_share_service(
        auth_repository=get_auth_repository(),
        report_share_repository=get_report_share_repository(),
    )


def get_session_overview_service():
    """세션 overview 서비스를 조립한다."""

    return service_builders.build_session_overview_service(
        session_repository=get_session_repository(),
        event_repository=get_event_repository(),
        utterance_repository=get_utterance_repository(),
        topic_summarizer=_get_shared_topic_summarizer(),
        recent_topic_utterance_count=settings.topic_summary_recent_utterance_count,
        min_topic_utterance_length=settings.topic_summary_min_utterance_length,
        min_topic_utterance_confidence=settings.topic_summary_min_utterance_confidence,
    )


def preload_runtime_services() -> None:
    """애플리케이션 시작 시 공통 STT 서비스를 preload한다."""

    return audio_runtime.preload_runtime_services(
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
    """실시간 스트림 워커 풀을 시작한다."""

    await get_live_stream_service().start()


async def shutdown_live_stream_service() -> None:
    """실시간 스트림 워커 풀과 컨텍스트를 정리한다."""

    service = get_live_stream_service()
    await service.shutdown()
    get_live_stream_service.cache_clear()


def _build_audio_pipeline_service(source: str):
    """입력 소스별 오디오 파이프라인을 구성한다."""

    return audio_runtime.build_audio_pipeline_service(
        source=source,
        settings=settings,
        resolve_audio_source_policy=resolve_audio_source_policy,
        speech_to_text_service=_get_speech_to_text_service(source),
        analyzer_service=_get_shared_analyzer(),
        utterance_repository=get_utterance_repository(),
        event_repository=get_event_repository(),
        transaction_manager=get_transaction_manager(),
        runtime_monitor_service=get_runtime_monitor_service(),
        live_event_corrector=_get_shared_live_event_corrector(),
    )


@lru_cache(maxsize=1)
def _get_shared_analyzer():
    return shared_factories.create_shared_analyzer(
        settings=settings,
        resolve_analyzer_service_profile=resolve_analyzer_service_profile,
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
    return audio_runtime.create_speech_to_text_service(
        source=source,
        settings=settings,
        logger=logger,
        resolve_speech_to_text_profile=resolve_speech_to_text_profile,
        resolve_stt_settings_for_source=_resolve_stt_settings_for_source,
        build_stt_build_options=_build_stt_build_options,
        create_speech_to_text_service_from_options=create_speech_to_text_service_from_options,
    )


def _build_stt_build_options(profile):
    return audio_runtime.build_stt_build_options(profile)


@lru_cache(maxsize=1)
def _get_shared_audio_preprocessor():
    return shared_factories.create_shared_audio_preprocessor(
        settings=settings,
        resolve_audio_preprocessor_profile=resolve_audio_preprocessor_profile,
    )


@lru_cache(maxsize=1)
def _get_shared_speaker_diarizer():
    return shared_factories.create_shared_speaker_diarizer(
        settings=settings,
        resolve_speaker_diarizer_profile=resolve_speaker_diarizer_profile,
    )


@lru_cache(maxsize=1)
def _get_shared_audio_postprocessing_service():
    return shared_factories.create_shared_audio_postprocessing_service(
        settings=settings,
        resolve_audio_source_policy=resolve_audio_source_policy,
        create_audio_preprocessor_service=_get_shared_audio_preprocessor,
        create_speaker_diarizer_service=_get_shared_speaker_diarizer,
        create_file_speech_to_text_service=lambda: _create_speech_to_text_service(
            AudioSource.FILE.value
        ),
        build_transcription_guard=_build_transcription_guard,
    )


@lru_cache(maxsize=1)
def _get_shared_speaker_event_projection_service():
    return shared_factories.create_shared_speaker_event_projection_service(
        analyzer_service=_get_shared_analyzer(),
    )


@lru_cache(maxsize=1)
def _get_shared_report_refiner():
    return shared_factories.create_shared_report_refiner(
        settings=settings,
        resolve_report_refiner_service_profile=resolve_report_refiner_service_profile,
    )


@lru_cache(maxsize=1)
def _get_shared_topic_summarizer():
    return shared_factories.create_shared_topic_summarizer(
        settings=settings,
        resolve_topic_summarizer_service_profile=resolve_topic_summarizer_service_profile,
    )


@lru_cache(maxsize=1)
def _get_shared_live_event_corrector():
    return shared_factories.create_shared_live_event_corrector(
        settings=settings,
        resolve_live_event_corrector_service_profile=resolve_live_event_corrector_service_profile,
        event_repository=get_event_repository(),
        transaction_manager=get_transaction_manager(),
    )


def _build_audio_segmenter(source_policy):
    return audio_runtime.build_audio_segmenter(
        source_policy=source_policy,
        settings=settings,
    )


def _build_audio_content_gate(source_policy):
    return audio_runtime.build_audio_content_gate(
        source_policy=source_policy,
        settings=settings,
    )


def _build_transcription_guard(source_policy):
    return audio_runtime.build_transcription_guard(
        source_policy=source_policy,
        settings=settings,
    )


def _resolve_stt_settings_for_source(source: str):
    return audio_runtime.resolve_stt_settings_for_source(
        source,
        settings=settings,
    )
