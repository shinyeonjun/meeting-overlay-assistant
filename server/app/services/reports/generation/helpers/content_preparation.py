"""회의록 본문 조립 facade."""

from __future__ import annotations

from pathlib import Path

from server.app.repositories.contracts.meeting_event_repository import (
    MeetingEventRepository,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.html_report_template import (
    render_report_html,
)
from server.app.services.reports.composition.report_document_mapper import (
    ReportSessionContext,
    build_report_document_v1,
)
from server.app.services.reports.composition.report_markdown_renderer import (
    render_report_markdown,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)
from server.app.services.reports.generation.helpers.content_preparation_helpers import (
    build_analysis_snapshot as assemble_analysis_snapshot,
    build_transcript_markdown as assemble_transcript_markdown,
    resolve_report_inputs,
)
from server.app.services.reports.report_models import (
    PreparedReportContent,
    ReportInsightResolution,
)


def prepare_report_content(
    *,
    session_id: str,
    audio_path: Path | None,
    live_events: list,
    canonical_speaker_transcript: list[SpeakerTranscriptSegment],
    event_repository: MeetingEventRepository,
    audio_postprocessing_service: AudioPostprocessingService | None,
    speaker_event_projection_service: SpeakerEventProjectionService | None,
    session_context: ReportSessionContext | None = None,
) -> PreparedReportContent:
    """회의록 공통 계산 결과를 한 번에 준비한다."""

    (
        speaker_transcript,
        speaker_events,
        report_insights,
        speaker_processing_error,
    ) = resolve_report_inputs(
        session_id=session_id,
        audio_path=audio_path,
        live_events=live_events,
        canonical_speaker_transcript=canonical_speaker_transcript,
        event_repository=event_repository,
        audio_postprocessing_service=audio_postprocessing_service,
        speaker_event_projection_service=speaker_event_projection_service,
    )
    report_document = build_report_document_v1(
        session_id=session_id,
        events=report_insights.events,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        insight_source=report_insights.insight_source,
        session_context=session_context,
    )
    markdown_content = render_report_markdown(
        session_id=session_id,
        document=report_document,
    )
    html_content = render_report_html(report_document)
    transcript_markdown = None
    analysis_snapshot = None
    if speaker_transcript:
        transcript_markdown = build_transcript_markdown(
            session_id=session_id,
            speaker_transcript=speaker_transcript,
        )
    if speaker_transcript or speaker_processing_error:
        analysis_snapshot = build_analysis_snapshot(
            session_id=session_id,
            insight_source=report_insights.insight_source,
            events=report_insights.events,
            speaker_transcript=speaker_transcript,
            speaker_events=speaker_events,
            refined_markdown=markdown_content,
            speaker_processing_error=speaker_processing_error,
        )
    return PreparedReportContent(
        markdown_content=markdown_content,
        report_document=report_document,
        html_content=html_content,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        insight_source=report_insights.insight_source,
        transcript_markdown=transcript_markdown,
        analysis_snapshot=analysis_snapshot,
        speaker_processing_error=speaker_processing_error,
    )


def build_transcript_markdown(
    *,
    session_id: str,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> str:
    """화자 전사 결과를 markdown artifact로 만든다."""

    return assemble_transcript_markdown(
        session_id=session_id,
        speaker_transcript=speaker_transcript,
    )


def build_analysis_snapshot(
    *,
    session_id: str,
    insight_source: str,
    events: list,
    speaker_transcript: list[SpeakerTranscriptSegment],
    speaker_events: list[SpeakerAttributedEvent],
    refined_markdown: str,
    speaker_processing_error: str | None = None,
) -> dict[str, object]:
    """회의록 생성 입력과 중간 결과 snapshot을 만든다."""

    return assemble_analysis_snapshot(
        session_id=session_id,
        insight_source=insight_source,
        events=events,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        refined_markdown=refined_markdown,
        speaker_processing_error=speaker_processing_error,
    )


__all__ = [
    "build_analysis_snapshot",
    "build_transcript_markdown",
    "prepare_report_content",
]
