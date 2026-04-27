"""회의록 정본 문서 생성에 필요한 입력 해석 helper."""

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
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)
from server.app.services.reports.generation.helpers.insight_resolution import (
    resolve_report_insights,
)
from server.app.services.reports.report_models import ReportInsightResolution


logger = logging.getLogger(__name__)


def resolve_report_inputs(
    *,
    session_id: str,
    audio_path: Path | None,
    live_events: list | None,
    canonical_speaker_transcript: list[SpeakerTranscriptSegment],
    event_repository: MeetingEventRepository,
    audio_postprocessing_service: AudioPostprocessingService | None,
    speaker_event_projection_service: SpeakerEventProjectionService | None,
) -> tuple[
    list[SpeakerTranscriptSegment],
    list[SpeakerAttributedEvent],
    ReportInsightResolution,
    str | None,
]:
    """이벤트와 화자 결과를 정본 문서 입력으로 정리한다."""

    resolved_live_events = live_events
    if resolved_live_events is None:
        resolved_live_events = event_repository.list_by_session(
            session_id,
            insight_scope="live",
        )
    speaker_transcript: list[SpeakerTranscriptSegment] = list(canonical_speaker_transcript)
    speaker_events: list[SpeakerAttributedEvent] = []
    speaker_processing_error: str | None = None

    if speaker_transcript:
        speaker_events = _build_speaker_events_from_events(resolved_live_events)
    elif audio_path is not None and audio_postprocessing_service is not None:
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
    return (
        speaker_transcript,
        speaker_events,
        report_insights,
        speaker_processing_error,
    )


def _build_speaker_events_from_events(
    events: list,
) -> list[SpeakerAttributedEvent]:
    attributed_events: list[SpeakerAttributedEvent] = []
    for event in events:
        speaker_label = event.speaker_label or "speaker-unknown"
        attributed_events.append(
            SpeakerAttributedEvent(
                speaker_label=speaker_label,
                event=event,
            )
        )
    return attributed_events
