"""HTTP 계층에서 공통 관련 reporting 구성을 담당한다."""
from __future__ import annotations

from server.app.api.http.dependency_providers.auth_context import (
    get_context_resolution_service,
    get_participant_followup_service,
    get_session_service,
)
from server.app.api.http.wiring import artifact_storage, job_queue, service_builders, shared_services
from server.app.api.http.wiring.persistence import (
    get_auth_repository,
    get_event_repository,
    get_knowledge_chunk_repository,
    get_knowledge_document_repository,
    get_note_correction_job_repository,
    get_report_generation_job_repository,
    get_report_repository,
    get_report_share_repository,
    get_session_post_processing_job_repository,
    get_session_repository,
    get_utterance_repository,
)
from server.app.core.config import ROOT_DIR, settings
from server.app.services.reports.refinement import TranscriptCorrectionStore


def get_event_management_service():
    """이벤트 관리 서비스를 조립한다."""

    return service_builders.build_event_management_service(
        meeting_event_repository=get_event_repository(),
    )


def get_event_lifecycle_service():
    """이벤트 생명주기 서비스를 조립한다."""

    return service_builders.build_event_lifecycle_service(
        meeting_event_repository=get_event_repository(),
    )


def get_report_service():
    """리포트 서비스를 조립한다."""

    return service_builders.build_report_service(
        event_repository=get_event_repository(),
        report_repository=get_report_repository(),
        utterance_repository=get_utterance_repository(),
        audio_postprocessing_service=shared_services.get_shared_audio_postprocessing_service(),
        speaker_event_projection_service=shared_services.get_shared_speaker_event_projection_service(),
        report_refiner=shared_services.get_shared_report_refiner(),
        artifact_store=artifact_storage.get_local_artifact_store(),
        transcript_correction_store=TranscriptCorrectionStore(
            artifact_storage.get_local_artifact_store()
        ),
    )


def get_report_generation_job_service():
    """리포트 생성 job 서비스를 조립한다."""

    return service_builders.build_report_generation_job_service(
        report_generation_job_repository=get_report_generation_job_repository(),
        note_correction_job_repository=get_note_correction_job_repository(),
        report_service=get_report_service(),
        report_knowledge_indexing_service=get_report_knowledge_indexing_service(),
        report_generation_job_queue=job_queue.get_report_generation_job_queue(),
        artifact_store=artifact_storage.get_local_artifact_store(),
        output_dir=ROOT_DIR / "server" / "data" / "reports",
    )


def get_note_correction_job_service():
    """노트 보정 job 서비스를 조립한다."""

    return service_builders.build_note_correction_job_service(
        note_correction_job_repository=get_note_correction_job_repository(),
        session_repository=get_session_repository(),
        utterance_repository=get_utterance_repository(),
        note_transcript_corrector=shared_services.get_shared_note_transcript_corrector,
        transcript_correction_store=TranscriptCorrectionStore(
            artifact_storage.get_local_artifact_store()
        ),
        report_generation_job_service=get_report_generation_job_service,
        note_correction_job_queue=job_queue.get_note_correction_job_queue(),
    )


def get_post_meeting_pipeline_recovery_service():
    """post-meeting 단계형 파이프라인 복구 서비스를 조립한다."""

    return service_builders.build_post_meeting_pipeline_recovery_service(
        session_repository=get_session_repository(),
        session_post_processing_job_service=get_session_post_processing_job_service(),
        note_correction_job_service=get_note_correction_job_service(),
        report_generation_job_service=get_report_generation_job_service(),
        max_attempts=settings.pipeline_job_max_attempts,
    )


def get_session_post_processing_job_service():
    """세션 후처리 job 서비스를 조립한다."""

    from server.app.services.post_meeting.session_post_processing_job_service import (
        SessionPostProcessingJobService,
    )

    return SessionPostProcessingJobService(
        repository=get_session_post_processing_job_repository(),
        session_repository=get_session_repository(),
        utterance_repository=get_utterance_repository(),
        event_repository=get_event_repository(),
        audio_postprocessing_service=shared_services.get_shared_audio_postprocessing_service,
        analyzer=shared_services.get_shared_analyzer,
        note_correction_job_service=get_note_correction_job_service,
        job_queue=job_queue.get_session_post_processing_job_queue(),
        artifact_store=artifact_storage.get_local_artifact_store(),
        transcript_correction_store=TranscriptCorrectionStore(
            artifact_storage.get_local_artifact_store()
        ),
    )


def get_report_knowledge_indexing_service():
    """리포트 knowledge indexing 서비스를 조립한다."""

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
        topic_summarizer=shared_services.get_shared_topic_summarizer(),
        recent_topic_utterance_count=settings.topic_summary_recent_utterance_count,
        min_topic_utterance_length=settings.topic_summary_min_utterance_length,
        min_topic_utterance_confidence=settings.topic_summary_min_utterance_confidence,
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


def get_session_finalization_service():
    """세션 종료 후속 서비스를 조립한다."""

    return service_builders.build_session_finalization_service(
        session_service=get_session_service(),
        session_post_processing_job_service=get_session_post_processing_job_service(),
        participant_followup_service=get_participant_followup_service(),
    )


def get_post_meeting_pipeline_service():
    """회의 종료 후처리 pipeline 서비스를 조립한다."""

    return service_builders.build_post_meeting_pipeline_service(
        session_service=get_session_service(),
        session_post_processing_job_service=get_session_post_processing_job_service(),
        participant_followup_service=get_participant_followup_service(),
    )
