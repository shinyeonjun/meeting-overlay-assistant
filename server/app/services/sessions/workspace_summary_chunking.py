"""workspace summary note entry chunking helper."""

from __future__ import annotations

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventType
from server.app.services.sessions.workspace_summary_selection import (
    _select_event_items_in_range,
)
from server.app.services.sessions.workspace_summary_types import (
    _SummaryChunk,
    _SummaryInputs,
)
from server.app.services.sessions.workspace_summary_utils import (
    _select_topic_candidates_for_range,
)


def build_summary_chunks(
    *,
    inputs: _SummaryInputs,
    utterances: list[Utterance],
    events: list[MeetingEvent],
    chunk_target_chars: int,
    chunk_overlap_utterances: int,
    max_chunk_count: int,
) -> list[_SummaryChunk]:
    """노트 entry 목록을 LLM 분석용 시간순 chunk로 나눈다."""

    note_entries = inputs.note_entries
    if not note_entries:
        return []

    utterance_by_id = {utterance.id: utterance for utterance in utterances}
    chunks: list[_SummaryChunk] = []
    start_index = 0

    while start_index < len(note_entries) and len(chunks) < max_chunk_count:
        end_index = _resolve_chunk_end_index(
            note_entries=note_entries,
            start_index=start_index,
            chunk_target_chars=chunk_target_chars,
            is_last_allowed_chunk=len(chunks) == max_chunk_count - 1,
        )

        selected_entries = note_entries[start_index : end_index + 1]
        chunk_start_ms = selected_entries[0].start_ms
        chunk_end_ms = selected_entries[-1].end_ms
        chunks.append(
            _SummaryChunk(
                index=len(chunks),
                start_ms=chunk_start_ms,
                end_ms=chunk_end_ms,
                note_excerpt="\n".join(item.rendered for item in selected_entries),
                topic_candidates=_select_topic_candidates_for_range(
                    inputs.topic_candidates,
                    start_ms=chunk_start_ms,
                    end_ms=chunk_end_ms,
                ),
                decisions=_select_event_items_in_range(
                    events,
                    utterance_by_id=utterance_by_id,
                    start_ms=chunk_start_ms,
                    end_ms=chunk_end_ms,
                    event_type=EventType.DECISION,
                    limit=3,
                ),
                next_actions=_select_event_items_in_range(
                    events,
                    utterance_by_id=utterance_by_id,
                    start_ms=chunk_start_ms,
                    end_ms=chunk_end_ms,
                    event_type=EventType.ACTION_ITEM,
                    limit=3,
                ),
                open_questions=_select_event_items_in_range(
                    events,
                    utterance_by_id=utterance_by_id,
                    start_ms=chunk_start_ms,
                    end_ms=chunk_end_ms,
                    event_type=None,
                    limit=2,
                    allowed_types={EventType.QUESTION, EventType.RISK},
                ),
            )
        )
        if end_index >= len(note_entries) - 1:
            break
        start_index = max(
            end_index + 1 - chunk_overlap_utterances,
            start_index + 1,
        )

    return chunks


def _resolve_chunk_end_index(
    *,
    note_entries,
    start_index: int,
    chunk_target_chars: int,
    is_last_allowed_chunk: bool,
) -> int:
    if is_last_allowed_chunk:
        return len(note_entries) - 1

    end_index = start_index
    total_chars = 0
    while end_index < len(note_entries):
        line_length = len(note_entries[end_index].rendered) + 1
        if total_chars > 0 and total_chars + line_length > chunk_target_chars:
            end_index -= 1
            break
        total_chars += line_length
        end_index += 1

    if end_index >= len(note_entries):
        end_index = len(note_entries) - 1
    elif end_index < start_index:
        end_index = start_index
    if end_index == start_index and start_index < len(note_entries) - 1:
        end_index = start_index + 1
    return end_index
