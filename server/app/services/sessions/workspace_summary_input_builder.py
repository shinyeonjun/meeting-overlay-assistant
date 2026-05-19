"""Workspace summary 입력, chunk, topic target 구성을 담당한다."""
from __future__ import annotations

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import EventType
from server.app.services.reports.refinement import TranscriptCorrectionDocument
from server.app.services.sessions.workspace_summary_selection import (
    _build_topic_candidates,
    _select_event_items,
    _select_event_items_in_range,
)
from server.app.services.sessions.workspace_summary_chunking import (
    build_summary_chunks,
)
from server.app.services.sessions.workspace_summary_types import (
    _NoteEntry,
    _SummaryChunk,
    _SummaryInputs,
    _TopicAnalysisTarget,
    _ReducedTopicSegment,
)
from server.app.services.sessions.workspace_summary_utils import (
    _format_ms,
    _ranges_overlap,
)


class WorkspaceSummaryInputBuilderMixin:
    """요약 생성을 위한 corrected note, chunk, topic target을 만든다."""

    def _build_inputs(
        self,
        *,
        session: MeetingSession,
        utterances: list[Utterance],
        correction_document: TranscriptCorrectionDocument | None,
        events: list[MeetingEvent],
    ) -> _SummaryInputs:
        corrected_text_by_id = {
            item.utterance_id: item.corrected_text.strip()
            for item in (correction_document.items if correction_document is not None else [])
            if item.corrected_text.strip()
        }

        note_entries: list[_NoteEntry] = []
        for utterance in utterances:
            text = corrected_text_by_id.get(utterance.id) or utterance.text.strip()
            if not text:
                continue
            speaker = utterance.speaker_label or "발화자 미상"
            note_entries.append(
                _NoteEntry(
                    utterance_id=utterance.id,
                    start_ms=utterance.start_ms,
                    end_ms=utterance.end_ms,
                    rendered=f"[{_format_ms(utterance.start_ms)}] {speaker}: {text}",
                )
            )

        topic_candidates = _build_topic_candidates(events=events, utterances=utterances)
        current_topic = str(topic_candidates[-1]["title"]) if topic_candidates else None

        return _SummaryInputs(
            headline_seed=(
                str(topic_candidates[0]["title"])
                if topic_candidates
                else current_topic or session.title
            ),
            note_entries=note_entries,
            current_topic=current_topic,
            topic_candidates=topic_candidates,
            decisions=_select_event_items(events, EventType.DECISION, limit=6),
            next_actions=_select_event_items(events, EventType.ACTION_ITEM, limit=6),
            open_questions=_select_event_items(
                events,
                None,
                limit=5,
                allowed_types={EventType.QUESTION, EventType.RISK},
            ),
        )

    def _build_chunks(
        self,
        *,
        inputs: _SummaryInputs,
        utterances: list[Utterance],
        events: list[MeetingEvent],
    ) -> list[_SummaryChunk]:
        return build_summary_chunks(
            inputs=inputs,
            utterances=utterances,
            events=events,
            chunk_target_chars=self._chunk_target_chars,
            chunk_overlap_utterances=self._chunk_overlap_utterances,
            max_chunk_count=self._max_chunk_count,
        )

    def _build_topic_analysis_targets(
        self,
        *,
        inputs: _SummaryInputs,
        events: list[MeetingEvent],
        chunks: list[_SummaryChunk],
        reduced_topics: list[_ReducedTopicSegment],
        utterances: list[Utterance],
    ) -> list[_TopicAnalysisTarget]:
        utterance_by_id = {utterance.id: utterance for utterance in utterances}
        targets: list[_TopicAnalysisTarget] = []
        for topic in reduced_topics:
            note_excerpt = self._build_note_excerpt_for_range(
                note_entries=inputs.note_entries,
                start_ms=topic.start_ms,
                end_ms=topic.end_ms,
            )
            if not note_excerpt:
                note_excerpt = "\n".join(
                    chunks[index].note_excerpt
                    for index in topic.chunk_indexes
                    if 0 <= index < len(chunks)
                )
            targets.append(
                _TopicAnalysisTarget(
                    source_index=topic.source_index,
                    title=topic.title,
                    start_ms=topic.start_ms,
                    end_ms=topic.end_ms,
                    chunk_indexes=topic.chunk_indexes,
                    note_excerpt=note_excerpt,
                    decisions=_select_event_items_in_range(
                        events,
                        utterance_by_id=utterance_by_id,
                        start_ms=topic.start_ms,
                        end_ms=topic.end_ms,
                        event_type=EventType.DECISION,
                        limit=4,
                    ),
                    next_actions=_select_event_items_in_range(
                        events,
                        utterance_by_id=utterance_by_id,
                        start_ms=topic.start_ms,
                        end_ms=topic.end_ms,
                        event_type=EventType.ACTION_ITEM,
                        limit=4,
                    ),
                    open_questions=_select_event_items_in_range(
                        events,
                        utterance_by_id=utterance_by_id,
                        start_ms=topic.start_ms,
                        end_ms=topic.end_ms,
                        event_type=None,
                        limit=3,
                        allowed_types={EventType.QUESTION, EventType.RISK},
                    ),
                )
            )
        return targets

    @staticmethod
    def _build_note_excerpt_for_range(
        *,
        note_entries: list[_NoteEntry],
        start_ms: int,
        end_ms: int,
    ) -> str:
        selected = [
            item.rendered
            for item in note_entries
            if _ranges_overlap(start_ms, end_ms, item.start_ms, item.end_ms)
        ]
        return "\n".join(selected)
