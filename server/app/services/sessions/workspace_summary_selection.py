"""workspace summary evidence/topic ?? ??."""

from __future__ import annotations

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventType
from server.app.services.sessions.workspace_summary_models import WorkspaceSummaryEvidence
from server.app.services.sessions.workspace_summary_utils import (
    _ranges_overlap,
    _should_skip_event_title,
)

def _select_event_items(
    events: list[MeetingEvent],
    event_type: EventType | None,
    *,
    limit: int,
    allowed_types: set[EventType] | None = None,
) -> list[dict[str, str | None]]:
    selected: list[dict[str, str | None]] = []
    for event in events:
        if allowed_types is not None:
            if event.event_type not in allowed_types:
                continue
        elif event_type is not None and event.event_type != event_type:
            continue

        title = event.title.strip()
        if not title or _should_skip_event_title(title, event.event_type):
            continue

        selected.append(
            {
                "title": title,
                "speaker_label": event.speaker_label,
                "state": event.state.value if hasattr(event.state, "value") else str(event.state),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _select_event_items_in_range(
    events: list[MeetingEvent],
    *,
    utterance_by_id: dict[str, Utterance],
    start_ms: int,
    end_ms: int,
    event_type: EventType | None,
    limit: int,
    allowed_types: set[EventType] | None = None,
) -> list[dict[str, str | None]]:
    selected: list[dict[str, str | None]] = []
    for event in events:
        if allowed_types is not None:
            if event.event_type not in allowed_types:
                continue
        elif event_type is not None and event.event_type != event_type:
            continue

        title = event.title.strip()
        if not title or _should_skip_event_title(title, event.event_type):
            continue

        utterance = utterance_by_id.get(event.source_utterance_id or "")
        if utterance is None or not _ranges_overlap(
            start_ms,
            end_ms,
            utterance.start_ms,
            utterance.end_ms,
        ):
            continue

        selected.append(
            {
                "title": title,
                "speaker_label": event.speaker_label,
                "state": event.state.value if hasattr(event.state, "value") else str(event.state),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _build_evidence(
    *,
    events: list[MeetingEvent],
    utterances: list[Utterance],
) -> list[WorkspaceSummaryEvidence]:
    utterance_by_id = {utterance.id: utterance for utterance in utterances}
    evidence: list[WorkspaceSummaryEvidence] = []
    for event in events:
        if event.event_type not in {
            EventType.DECISION,
            EventType.ACTION_ITEM,
            EventType.QUESTION,
            EventType.RISK,
        }:
            continue
        utterance = utterance_by_id.get(event.source_utterance_id or "")
        if utterance is None:
            continue
        evidence.append(
            WorkspaceSummaryEvidence(
                label=event.title.strip() or "다시 볼 구간",
                start_ms=utterance.start_ms,
                end_ms=utterance.end_ms,
            )
        )
        if len(evidence) >= 3:
            break
    return evidence


def _build_topic_candidates(
    *,
    events: list[MeetingEvent],
    utterances: list[Utterance],
    max_candidates: int = 8,
) -> list[dict[str, int | str]]:
    utterance_by_id = {utterance.id: utterance for utterance in utterances}
    last_utterance_end_ms = max((utterance.end_ms for utterance in utterances), default=0)

    topic_events = [
        event
        for event in events
        if event.event_type == EventType.TOPIC and event.title.strip()
    ]
    if not topic_events:
        return []

    def sort_key(event: MeetingEvent) -> tuple[int, int]:
        utterance = utterance_by_id.get(event.source_utterance_id or "")
        if utterance is not None:
            return (utterance.start_ms, utterance.end_ms)
        return (event.created_at_ms, event.updated_at_ms)

    sorted_events = sorted(topic_events, key=sort_key)
    timeline: list[dict[str, int | str]] = []

    for index, event in enumerate(sorted_events):
        utterance = utterance_by_id.get(event.source_utterance_id or "")
        start_ms = utterance.start_ms if utterance is not None else sort_key(event)[0]
        own_end_ms = utterance.end_ms if utterance is not None else start_ms

        if index + 1 < len(sorted_events):
            next_start_ms = sort_key(sorted_events[index + 1])[0]
            end_ms = max(own_end_ms, next_start_ms - 1)
        else:
            end_ms = max(own_end_ms, last_utterance_end_ms)

        title = event.title.strip()
        if timeline and timeline[-1]["title"] == title:
            timeline[-1]["end_ms"] = max(int(timeline[-1]["end_ms"]), end_ms)
            continue

        timeline.append(
            {
                "source_index": len(timeline),
                "title": title,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )

    return timeline[:max_candidates]
