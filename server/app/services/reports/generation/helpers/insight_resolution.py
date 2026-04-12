"""리포트 영역의 insight resolution 서비스를 제공한다."""
from __future__ import annotations

from server.app.domain.shared.enums import EventState, EventType
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.report_models import ReportInsightResolution


def resolve_report_insights(
    *,
    live_events: list,
    speaker_events: list[SpeakerAttributedEvent],
) -> ReportInsightResolution:
    """리포트에 사용할 이벤트 집합과 insight source를 결정한다."""

    def is_reportable(event) -> bool:
        if event.event_type == EventType.DECISION:
            return event.state in {EventState.CONFIRMED, EventState.UPDATED, EventState.CLOSED}
        if event.event_type == EventType.ACTION_ITEM:
            return event.state in {EventState.OPEN, EventState.CLOSED}
        if event.event_type == EventType.QUESTION:
            return event.state in {EventState.OPEN, EventState.ANSWERED, EventState.CLOSED}
        if event.event_type == EventType.RISK:
            return event.state in {EventState.OPEN, EventState.RESOLVED, EventState.CLOSED}
        return event.state != EventState.CLOSED

    if speaker_events:
        if any(
            getattr(item.event, "event_source", "") == "post_processed"
            or getattr(item.event, "insight_scope", "") == "finalized"
            for item in speaker_events
        ):
            return ReportInsightResolution(
                events=[item.event for item in speaker_events if is_reportable(item.event)],
                insight_source="high_precision_audio",
            )
        return ReportInsightResolution(
            events=[item.event for item in speaker_events if is_reportable(item.event)],
            insight_source="high_precision_audio",
        )
    return ReportInsightResolution(
        events=[event for event in live_events if is_reportable(event)],
        insight_source="live_fallback",
    )
