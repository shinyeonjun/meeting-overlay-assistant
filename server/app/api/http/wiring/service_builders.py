"""도메인 서비스 조립 보조 함수."""

from __future__ import annotations

from server.app.services.audio.pipeline.audio_pipeline_service import AudioPipelineService
from server.app.services.auth.auth_service import AuthService
from server.app.services.context.context_catalog_service import ContextCatalogService
from server.app.services.context.context_resolution_service import ContextResolutionService
from server.app.services.context.meeting_context_service import MeetingContextService
from server.app.services.events.event_lifecycle_service import EventLifecycleService
from server.app.services.events.event_management_service import EventManagementService
from server.app.services.history import CarryOverService, HistoryQueryService
from server.app.services.observability.runtime_monitor_service import RuntimeMonitorService
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.participation.participation_query_service import (
    ParticipationQueryService,
)
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)
from server.app.services.post_meeting.post_meeting_pipeline_service import (
    PostMeetingPipelineService,
)
from server.app.services.retrieval import (
    MarkdownChunker,
    OllamaEmbeddingService,
    ReportKnowledgeIndexingService,
    RetrievalQueryService,
)
from server.app.services.reports.composition.markdown_report_builder import (
    MarkdownReportBuilder,
)
from server.app.services.reports.core.report_service import ReportService
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)
from server.app.services.reports.sharing.report_share_service import ReportShareService
from server.app.services.sessions.overview_builder import SessionOverviewBuilder
from server.app.services.sessions.session_finalization_service import (
    SessionFinalizationService,
)
from server.app.services.sessions.session_overview_service import SessionOverviewService
from server.app.services.sessions.session_service import SessionService


def build_auth_service(*, auth_repository, session_ttl_hours: int) -> AuthService:
    """인증 서비스를 조립한다."""

    return AuthService(
        repository=auth_repository,
        session_ttl_hours=session_ttl_hours,
    )


def build_session_service(*, session_repository, meeting_context_repository) -> SessionService:
    """세션 서비스를 조립한다."""

    return SessionService(
        session_repository,
        meeting_context_repository,
    )


def build_meeting_context_service(*, meeting_context_repository) -> MeetingContextService:
    """회사/상대방/스레드 맥락 서비스를 조립한다."""

    return MeetingContextService(meeting_context_repository)


def build_context_catalog_service(*, meeting_context_repository) -> ContextCatalogService:
    """맥락 정본 catalog 서비스를 조립한다."""

    return ContextCatalogService(meeting_context_repository)


def build_context_resolution_service(*, meeting_context_repository) -> ContextResolutionService:
    """세션용 맥락 정합성 해결 서비스를 조립한다."""

    return ContextResolutionService(
        build_context_catalog_service(meeting_context_repository=meeting_context_repository)
    )


def build_participant_followup_service(
    *,
    participant_followup_repository,
    meeting_context_repository,
) -> ParticipantFollowupService:
    """참여자 후속 작업 서비스를 조립한다."""

    return ParticipantFollowupService(
        participant_followup_repository=participant_followup_repository,
        participant_resolution_service=ParticipantResolutionService(
            meeting_context_repository=meeting_context_repository,
        ),
    )


def build_participation_query_service(
    *,
    meeting_context_repository,
    participant_followup_repository,
) -> ParticipationQueryService:
    """참여자 상세 조회 서비스를 조립한다."""

    participant_resolution_service = ParticipantResolutionService(
        meeting_context_repository=meeting_context_repository,
    )
    participant_followup_service = ParticipantFollowupService(
        participant_followup_repository=participant_followup_repository,
        participant_resolution_service=participant_resolution_service,
    )
    return ParticipationQueryService(
        participant_resolution_service=participant_resolution_service,
        participant_followup_service=participant_followup_service,
    )


def build_runtime_monitor_service() -> RuntimeMonitorService:
    """런타임 운영 지표 수집기를 만든다."""

    return RuntimeMonitorService()


def build_session_finalization_service(
    *,
    session_service: SessionService,
    report_generation_job_service: ReportGenerationJobService,
    participant_followup_service: ParticipantFollowupService,
) -> SessionFinalizationService:
    """세션 종료와 최종 리포트 생성을 묶은 서비스를 조립한다."""

    return SessionFinalizationService(
        session_service=session_service,
        report_generation_job_service=report_generation_job_service,
        participant_followup_service=participant_followup_service,
    )


def build_post_meeting_pipeline_service(
    *,
    session_service: SessionService,
    report_generation_job_service: ReportGenerationJobService,
    participant_followup_service: ParticipantFollowupService,
) -> PostMeetingPipelineService:
    """회의 종료 후 후처리 pipeline 서비스를 조립한다."""

    return PostMeetingPipelineService(
        session_service=session_service,
        report_generation_job_service=report_generation_job_service,
        participant_followup_service=participant_followup_service,
    )


def build_event_management_service(*, meeting_event_repository) -> EventManagementService:
    """이벤트 관리 서비스를 조립한다."""

    return EventManagementService(meeting_event_repository)


def build_event_lifecycle_service(*, meeting_event_repository) -> EventLifecycleService:
    """이벤트 상태 전이 서비스를 조립한다."""

    return EventLifecycleService(meeting_event_repository)


def build_history_query_service(
    *,
    session_service: SessionService,
    report_service: ReportService,
    context_resolution_service: ContextResolutionService,
    event_management_service: EventManagementService,
    retrieval_query_service=None,
) -> HistoryQueryService:
    """history 타임라인 조회 서비스를 조립한다."""

    return HistoryQueryService(
        session_service=session_service,
        report_service=report_service,
        context_resolution_service=context_resolution_service,
        carry_over_service=CarryOverService(event_management_service),
        retrieval_query_service=retrieval_query_service,
    )


def build_report_service(
    *,
    event_repository,
    report_repository,
    audio_postprocessing_service,
    speaker_event_projection_service,
    report_refiner,
) -> ReportService:
    """리포트 서비스를 조립한다."""

    return ReportService(
        event_repository=event_repository,
        report_repository=report_repository,
        markdown_report_builder=MarkdownReportBuilder(),
        audio_postprocessing_service=audio_postprocessing_service,
        speaker_event_projection_service=speaker_event_projection_service,
        report_refiner=report_refiner,
    )


def build_report_generation_job_service(
    *,
    report_generation_job_repository,
    report_service: ReportService,
    report_knowledge_indexing_service,
    output_dir,
) -> ReportGenerationJobService:
    """리포트 생성 job 서비스를 조립한다."""

    return ReportGenerationJobService(
        repository=report_generation_job_repository,
        report_service=report_service,
        report_knowledge_indexing_service=report_knowledge_indexing_service,
        output_dir=output_dir,
    )


def build_report_knowledge_indexing_service(
    *,
    session_repository,
    knowledge_document_repository,
    knowledge_chunk_repository,
    embedding_service,
    chunk_target_chars: int,
    chunk_overlap_chars: int,
) -> ReportKnowledgeIndexingService | None:
    """리포트 -> knowledge 인덱싱 서비스를 조립한다."""

    if (
        session_repository is None
        or knowledge_document_repository is None
        or knowledge_chunk_repository is None
        or embedding_service is None
    ):
        return None

    return ReportKnowledgeIndexingService(
        session_repository=session_repository,
        knowledge_document_repository=knowledge_document_repository,
        knowledge_chunk_repository=knowledge_chunk_repository,
        embedding_service=embedding_service,
        markdown_chunker=MarkdownChunker(
            target_chars=chunk_target_chars,
            overlap_chars=chunk_overlap_chars,
        ),
    )


def build_retrieval_query_service(
    *,
    knowledge_chunk_repository,
    embedding_service,
    candidate_limit: int,
) -> RetrievalQueryService | None:
    """retrieval 검색 서비스를 조립한다."""

    if knowledge_chunk_repository is None or embedding_service is None:
        return None

    return RetrievalQueryService(
        knowledge_chunk_repository=knowledge_chunk_repository,
        embedding_service=embedding_service,
        candidate_limit=candidate_limit,
    )


def build_ollama_embedding_service(
    *,
    base_url: str | None,
    model: str,
    timeout_seconds: int,
):
    """Ollama embedding 서비스를 조립한다."""

    if not base_url:
        return None

    return OllamaEmbeddingService(
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def build_report_share_service(*, auth_repository, report_share_repository) -> ReportShareService:
    """리포트 공유 서비스를 조립한다."""

    return ReportShareService(
        auth_repository=auth_repository,
        report_share_repository=report_share_repository,
    )


def build_session_overview_service(
    *,
    session_repository,
    event_repository,
    utterance_repository,
    topic_summarizer,
    recent_topic_utterance_count: int,
    min_topic_utterance_length: int,
    min_topic_utterance_confidence: float,
) -> SessionOverviewService:
    """세션 overview 서비스를 조립한다."""

    return SessionOverviewService(
        session_repository=session_repository,
        event_repository=event_repository,
        utterance_repository=utterance_repository,
        overview_builder=SessionOverviewBuilder(),
        topic_summarizer=topic_summarizer,
        recent_topic_utterance_count=recent_topic_utterance_count,
        min_topic_utterance_length=min_topic_utterance_length,
        min_topic_utterance_confidence=min_topic_utterance_confidence,
    )


def build_text_input_pipeline_service(
    *,
    analyzer_service,
    event_repository,
    utterance_repository,
    transcription_guard,
    transaction_manager,
    runtime_monitor_service,
    placeholder_pipeline_factory,
) -> AudioPipelineService:
    """텍스트 입력 파이프라인 서비스를 조립한다."""

    return placeholder_pipeline_factory(
        analyzer_service=analyzer_service,
        event_repository=event_repository,
        utterance_repository=utterance_repository,
        transcription_guard=transcription_guard,
        transaction_manager=transaction_manager,
        runtime_monitor_service=runtime_monitor_service,
    )
