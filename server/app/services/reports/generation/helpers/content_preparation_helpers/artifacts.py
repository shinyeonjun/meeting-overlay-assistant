"""리포트 영역의 artifacts 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)


def build_transcript_markdown(
    *,
    session_id: str,
    speaker_transcript: list[SpeakerTranscriptSegment],
) -> str:
    """화자 전사 결과를 markdown artifact로 만든다."""

    lines = [
        "# 교정된 전사 결과",
        "",
        f"- 세션 ID: {session_id}",
        f"- 전사 구간 수: {len(speaker_transcript)}",
        "",
    ]
    for segment in speaker_transcript:
        lines.append(
            f"- [{segment.speaker_label}] "
            f"{segment.start_ms}ms-{segment.end_ms}ms "
            f"(confidence={segment.confidence:.3f})"
        )
        lines.append(f"  {segment.text}")
    return "\n".join(lines)


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

    return {
        "session_id": session_id,
        "insight_source": insight_source,
        "event_count": len(events),
        "speaker_transcript_count": len(speaker_transcript),
        "speaker_event_count": len(speaker_events),
        "speaker_processing_error": speaker_processing_error,
        "events": [
            {
                "event_type": event.event_type.value,
                "title": event.title,
                "state": event.state.value,
                "speaker_label": event.speaker_label,
                "input_source": event.input_source,
                "evidence_text": event.evidence_text,
            }
            for event in events
        ],
        "speaker_transcript": [
            {
                "speaker_label": segment.speaker_label,
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "text": segment.text,
                "confidence": segment.confidence,
            }
            for segment in speaker_transcript
        ],
        "speaker_events": [
            {
                "speaker_label": item.speaker_label,
                "event_type": item.event.event_type.value,
                "title": item.event.title,
                "state": item.event.state.value,
            }
            for item in speaker_events
        ],
        "refined_markdown": refined_markdown,
    }
