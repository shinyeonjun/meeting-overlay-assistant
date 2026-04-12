"""리포트 markdown 정제 helper."""

from __future__ import annotations

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
    ReportRefiner,
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

    if report_refiner is None:
        return raw_markdown

    return report_refiner.refine(
        ReportRefinementInput(
            session_id=session_id,
            raw_markdown=raw_markdown,
            events=[
                ReportRefinementEvent(
                    event_type=event.event_type.value,
                    title=event.title,
                    state=event.state.value,
                    evidence_text=event.evidence_text,
                    speaker_label=event.speaker_label,
                    input_source=event.input_source,
                )
                for event in events
            ],
            event_lines=[f"[{event.event_type.value}] {event.title}" for event in events],
            speaker_transcript_lines=[
                (
                    f"[{segment.speaker_label}] "
                    f"{format_timeline_range(segment.start_ms, segment.end_ms)} "
                    f"{segment.text}"
                )
                for segment in speaker_transcript
            ],
            speaker_event_lines=[
                f"[{item.event.event_type.value}] {item.speaker_label}: {item.event.title}"
                for item in speaker_events
            ],
        )
    )


def format_timeline_range(start_ms: int, end_ms: int) -> str:
    """밀리초 구간을 mm:ss-mm:ss 문자열로 변환한다."""

    return f"{format_mmss(start_ms)}-{format_mmss(end_ms)}"


def format_mmss(value_ms: int) -> str:
    """밀리초를 mm:ss 문자열로 변환한다."""

    total_seconds = max(int(value_ms // 1000), 0)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"
