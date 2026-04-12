"""리포트 영역의 content preparation 서비스를 제공한다."""
from __future__ import annotations

from pathlib import Path

from server.app.repositories.contracts.meeting_event_repository import (
    MeetingEventRepository,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.markdown_report_builder import (
    MarkdownReportBuilder,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)
from server.app.services.reports.generation.helpers.content_preparation_helpers import (
    build_analysis_snapshot as assemble_analysis_snapshot,
    build_transcript_markdown as assemble_transcript_markdown,
    compose_raw_markdown as build_raw_markdown,
    format_mmss as format_mmss_value,
    format_timeline_range as format_timeline,
    refine_markdown as refine_report_markdown,
)
from server.app.services.reports.refinement.report_refiner import ReportRefiner
from server.app.services.reports.report_models import (
    PreparedReportContent,
    ReportInsightResolution,
)


def prepare_report_content(
    *,
    session_id: str,
    audio_path: Path | None,
    live_events: list,
    reference_transcript_lines: list[str],
    canonical_speaker_transcript: list[SpeakerTranscriptSegment],
    event_repository: MeetingEventRepository,
    markdown_report_builder: MarkdownReportBuilder,
    audio_postprocessing_service: AudioPostprocessingService | None,
    speaker_event_projection_service: SpeakerEventProjectionService | None,
    report_refiner: ReportRefiner | None,
) -> PreparedReportContent:
    """리포트 공통 계산 결과를 한 번에 준비한다."""

    (
        raw_markdown,
        speaker_transcript,
        speaker_events,
        report_insights,
        speaker_processing_error,
    ) = compose_raw_markdown(
        session_id=session_id,
        audio_path=audio_path,
        live_events=live_events,
        reference_transcript_lines=reference_transcript_lines,
        canonical_speaker_transcript=canonical_speaker_transcript,
        event_repository=event_repository,
        markdown_report_builder=markdown_report_builder,
        audio_postprocessing_service=audio_postprocessing_service,
        speaker_event_projection_service=speaker_event_projection_service,
    )
    markdown_content = refine_markdown(
        session_id=session_id,
        raw_markdown=raw_markdown,
        events=report_insights.events,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        report_refiner=report_refiner,
    )
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
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        insight_source=report_insights.insight_source,
        transcript_markdown=transcript_markdown,
        analysis_snapshot=analysis_snapshot,
        speaker_processing_error=speaker_processing_error,
    )


def compose_raw_markdown(
    *,
    session_id: str,
    audio_path: Path | None,
    live_events: list | None,
    reference_transcript_lines: list[str],
    canonical_speaker_transcript: list[SpeakerTranscriptSegment],
    event_repository: MeetingEventRepository,
    markdown_report_builder: MarkdownReportBuilder,
    audio_postprocessing_service: AudioPostprocessingService | None,
    speaker_event_projection_service: SpeakerEventProjectionService | None,
) -> tuple[
    str,
    list[SpeakerTranscriptSegment],
    list[SpeakerAttributedEvent],
    ReportInsightResolution,
    str | None,
]:
    """이벤트와 전사 결과를 모아 raw markdown를 만든다."""

    return build_raw_markdown(
        session_id=session_id,
        audio_path=audio_path,
        live_events=live_events,
        reference_transcript_lines=reference_transcript_lines,
        canonical_speaker_transcript=canonical_speaker_transcript,
        event_repository=event_repository,
        markdown_report_builder=markdown_report_builder,
        audio_postprocessing_service=audio_postprocessing_service,
        speaker_event_projection_service=speaker_event_projection_service,
    )


def refine_markdown(
    *,
    session_id: str,
    raw_markdown: str,
    events: list,
    speaker_transcript: list[SpeakerTranscriptSegment],
    speaker_events: list[SpeakerAttributedEvent],
    report_refiner: ReportRefiner | None,
) -> str:
    """필요하면 refiner를 통해 raw markdown를 정제한다."""

    return refine_report_markdown(
        session_id=session_id,
        raw_markdown=raw_markdown,
        events=events,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        report_refiner=report_refiner,
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


def format_timeline_range(start_ms: int, end_ms: int) -> str:
    """밀리초 구간을 mm:ss-mm:ss 문자열로 변환한다."""

    return format_timeline(start_ms, end_ms)


def format_mmss(value_ms: int) -> str:
    """밀리초를 mm:ss 문자열로 변환한다."""

    return format_mmss_value(value_ms)


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
    """리포트 생성 입력과 중간 결과 snapshot을 만든다."""

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
    "compose_raw_markdown",
    "format_mmss",
    "format_timeline_range",
    "prepare_report_content",
    "refine_markdown",
]
