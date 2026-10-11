"""reporting 바운디드 컨텍스트의 공개 API.

다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any


_LAZY_NAMES = {
    "AudioPostprocessingService": "server.app.contexts.reporting.application.audio.audio_postprocessing_service",
    "BuiltMarkdownReport": "server.app.contexts.reporting.application.report_models",
    "DuplicateReportShareError": "server.app.contexts.reporting.application.sharing.report_share_service",
    "FinalReportStatus": "server.app.contexts.reporting.application.report_models",
    "InvalidReportShareTargetError": "server.app.contexts.reporting.application.sharing.report_share_service",
    "LLMMarkdownReportRefiner": "server.app.contexts.reporting.application.refinement.llm_markdown_report_refiner",
    "MarkdownReportBuilder": "server.app.contexts.reporting.application.composition.markdown_report_builder",
    "NoOpReportRefiner": "server.app.contexts.reporting.application.refinement.noop_report_refiner",
    "NoteCorrectionJobService": "server.app.contexts.reporting.application.jobs.note_correction_job_service",
    "NoteTranscriptCorrectionConfig": "server.app.contexts.reporting.application.refinement.note_transcript_corrector",
    "NoteTranscriptCorrector": "server.app.contexts.reporting.application.refinement.note_transcript_corrector",
    "PostMeetingPipelineRecoveryService": "server.app.contexts.reporting.application.jobs.post_meeting_pipeline_recovery_service",
    "ReportGenerationJobService": "server.app.contexts.reporting.application.jobs.report_generation_job_service",
    "ReportQueryService": "server.app.contexts.reporting.application.query.report_query_service",
    "ReportRefinementEvent": "server.app.contexts.reporting.application.refinement.report_refiner",
    "ReportRefinementInput": "server.app.contexts.reporting.application.refinement.report_refiner",
    "ReportService": "server.app.contexts.reporting.application.core.report_service",
    "ReportShareService": "server.app.contexts.reporting.application.sharing.report_share_service",
    "SessionReportSummary": "server.app.contexts.reporting.application.report_models",
    "ShareRecipientNotFoundError": "server.app.contexts.reporting.application.sharing.report_share_service",
    "SpeakerAttributedEvent": "server.app.contexts.reporting.application.composition.speaker_event_projection_service",
    "SpeakerEventProjectionService": "server.app.contexts.reporting.application.composition.speaker_event_projection_service",
    "SpeakerTranscriptSegment": "server.app.contexts.reporting.application.audio.audio_postprocessing_service",
    "StructuredMarkdownReportRefiner": "server.app.contexts.reporting.application.refinement.structured_markdown_report_refiner",
    "TranscriptCorrectionDocument": "server.app.contexts.reporting.application.refinement.transcript_correction_store",
    "TranscriptCorrectionItem": "server.app.contexts.reporting.application.refinement.transcript_correction_store",
    "TranscriptCorrectionStore": "server.app.contexts.reporting.application.refinement.transcript_correction_store",
    "build_final_report_status": "server.app.contexts.reporting.application.jobs.helpers.final_status",
    "create_report_refiner": "server.app.contexts.reporting.application.refinement.report_refiner_factory",
    "resolve_report_generation_readiness": "server.app.contexts.reporting.application.generation.helpers.generation_readiness",
    "utc_after_seconds_iso": "server.app.contexts.reporting.application.jobs.helpers.time_utils",
    "utc_now_iso": "server.app.contexts.reporting.application.jobs.helpers.time_utils",
}

__all__ = [
    "AudioPostprocessingService",
    "BuiltMarkdownReport",
    "DuplicateReportShareError",
    "FinalReportStatus",
    "InvalidReportShareTargetError",
    "LLMMarkdownReportRefiner",
    "MarkdownReportBuilder",
    "NoOpReportRefiner",
    "NoteCorrectionJobService",
    "NoteTranscriptCorrectionConfig",
    "NoteTranscriptCorrector",
    "PostMeetingPipelineRecoveryService",
    "ReportGenerationJobService",
    "ReportQueryService",
    "ReportRefinementEvent",
    "ReportRefinementInput",
    "ReportService",
    "ReportShareService",
    "SessionReportSummary",
    "ShareRecipientNotFoundError",
    "SpeakerAttributedEvent",
    "SpeakerEventProjectionService",
    "SpeakerTranscriptSegment",
    "StructuredMarkdownReportRefiner",
    "TranscriptCorrectionDocument",
    "TranscriptCorrectionItem",
    "TranscriptCorrectionStore",
    "build_final_report_status",
    "create_report_refiner",
    "resolve_report_generation_readiness",
    "utc_after_seconds_iso",
    "utc_now_iso",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_NAMES:
        return getattr(import_module(_LAZY_NAMES[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
