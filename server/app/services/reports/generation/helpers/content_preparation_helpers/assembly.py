"""리포트 raw markdown 조립 helper."""

from __future__ import annotations

import logging
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
from server.app.services.reports.generation.helpers.insight_resolution import (
    resolve_report_insights,
)
from server.app.services.reports.report_models import ReportInsightResolution


logger = logging.getLogger(__name__)


def compose_raw_markdown(
    *,
    session_id: str,
    audio_path: Path | None,
    live_events: list | None,
    reference_transcript_lines: list[str],
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
    """이벤트와 화자 결과를 모아 raw markdown를 만든다."""

    resolved_live_events = live_events
    if resolved_live_events is None:
        resolved_live_events = event_repository.list_by_session(
            session_id,
            insight_scope="live",
        )
    speaker_transcript: list[SpeakerTranscriptSegment] = []
    speaker_events: list[SpeakerAttributedEvent] = []
    speaker_processing_error: str | None = None

    if audio_path is not None and audio_postprocessing_service is not None:
        try:
            speaker_transcript = audio_postprocessing_service.build_speaker_transcript(audio_path)
            if speaker_event_projection_service is not None:
                speaker_events = speaker_event_projection_service.project(
                    session_id=session_id,
                    speaker_transcript=speaker_transcript,
                )
        except Exception as error:
            speaker_processing_error = str(error)
            logger.exception(
                "화자 분리 후처리 실패: session_id=%s audio_path=%s",
                session_id,
                audio_path,
            )

    report_insights = resolve_report_insights(
        live_events=resolved_live_events,
        speaker_events=speaker_events,
    )
    raw_markdown = markdown_report_builder.build(
        session_id=session_id,
        events=report_insights.events,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        reference_transcript_lines=reference_transcript_lines,
    )
    return (
        raw_markdown,
        speaker_transcript,
        speaker_events,
        report_insights,
        speaker_processing_error,
    )
