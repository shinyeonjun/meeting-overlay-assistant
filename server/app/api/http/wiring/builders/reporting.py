"""HTTP 계층에서 공통 관련 reporting 구성을 담당한다."""
from __future__ import annotations

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
from server.app.services.reports.jobs.note_correction_job_service import (
    NoteCorrectionJobService,
)
from server.app.services.reports.jobs.post_meeting_pipeline_recovery_service import (
    PostMeetingPipelineRecoveryService,
)
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)
from server.app.services.reports.sharing.report_share_service import ReportShareService
from server.app.services.sessions.overview_builder import SessionOverviewBuilder
from server.app.services.sessions.session_overview_service import SessionOverviewService
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


def build_report_service(
    *,
    session_repository,
    event_repository,
    report_repository,
    utterance_repository,
    audio_postprocessing_service,
    speaker_event_projection_service,
    report_refiner,
    artifact_store=None,
    transcript_correction_store=None,
) -> ReportService:
    """리포트 서비스를 조립한다."""

    return ReportService(
        event_repository=event_repository,
        report_repository=report_repository,
        markdown_report_builder=MarkdownReportBuilder(),
        session_repository=session_repository,
        utterance_repository=utterance_repository,
        audio_postprocessing_service=audio_postprocessing_service,
        speaker_event_projection_service=speaker_event_projection_service,
        report_refiner=report_refiner,
        artifact_store=artifact_store,
        transcript_correction_store=transcript_correction_store,
    )


def build_report_generation_job_service(
    *,
    report_generation_job_repository,
    session_post_processing_job_repository,
    note_correction_job_repository,
    report_service,
    report_knowledge_indexing_service,
    report_generation_job_queue,
    artifact_store,
    output_dir,
) -> ReportGenerationJobService:
    """리포트 생성 job 서비스를 조립한다."""

    return ReportGenerationJobService(
        repository=report_generation_job_repository,
        session_post_processing_job_repository=session_post_processing_job_repository,
        note_correction_job_repository=note_correction_job_repository,
        report_service=report_service,
        report_knowledge_indexing_service=report_knowledge_indexing_service,
        job_queue=report_generation_job_queue,
        artifact_store=artifact_store,
        output_dir=output_dir,
    )


def build_note_correction_job_service(
    *,
    note_correction_job_repository,
    session_repository,
    session_post_processing_job_repository,
    gpu_heavy_execution_gate,
    workspace_summary_wait_timeout_seconds,
    workspace_summary_poll_interval_seconds,
    utterance_repository,
    event_repository,
    note_transcript_corrector,
    transcript_correction_store,
    workspace_summary_synthesizer,
    workspace_summary_store,
    report_generation_job_service,
    note_correction_job_queue,
) -> NoteCorrectionJobService:
    """노트 보정 job 서비스를 조립한다."""

    return NoteCorrectionJobService(
        repository=note_correction_job_repository,
        session_repository=session_repository,
        session_post_processing_job_repository=session_post_processing_job_repository,
        gpu_heavy_execution_gate=gpu_heavy_execution_gate,
        workspace_summary_wait_timeout_seconds=workspace_summary_wait_timeout_seconds,
        workspace_summary_poll_interval_seconds=workspace_summary_poll_interval_seconds,
        utterance_repository=utterance_repository,
        event_repository=event_repository,
        note_transcript_corrector=note_transcript_corrector,
        transcript_correction_store=transcript_correction_store,
        workspace_summary_synthesizer=workspace_summary_synthesizer,
        workspace_summary_store=workspace_summary_store,
        report_generation_job_service=report_generation_job_service,
        job_queue=note_correction_job_queue,
    )


def build_post_meeting_pipeline_recovery_service(
    *,
    session_repository,
    session_post_processing_job_service,
    note_correction_job_service,
    report_generation_job_service,
    max_attempts: int,
) -> PostMeetingPipelineRecoveryService:
    """post-meeting 단계형 파이프라인 복구 서비스를 조립한다."""

    return PostMeetingPipelineRecoveryService(
        session_repository=session_repository,
        session_post_processing_job_service=session_post_processing_job_service,
        note_correction_job_service=note_correction_job_service,
        report_generation_job_service=report_generation_job_service,
        max_attempts=max_attempts,
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
    """리포트를 knowledge index로 적재하는 서비스를 조립한다."""

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
    """retrieval query 서비스를 조립한다."""

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
    workspace_summary_store: WorkspaceSummaryStore | None,
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
        workspace_summary_store=workspace_summary_store,
        recent_topic_utterance_count=recent_topic_utterance_count,
        min_topic_utterance_length=min_topic_utterance_length,
        min_topic_utterance_confidence=min_topic_utterance_confidence,
    )
