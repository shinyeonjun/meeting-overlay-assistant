"""?????? ?? ??? ?? ?? synthesizer."""

from __future__ import annotations

import json
import logging
import time

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import EventType
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.refinement import TranscriptCorrectionDocument
from server.app.services.sessions.workspace_summary_models import WorkspaceSummaryDocument
from server.app.services.sessions.workspace_summary_prompting import (
    _CHUNK_TOPIC_ANALYSIS_RESPONSE_SCHEMA,
    _CHUNK_TOPIC_ANALYSIS_SYSTEM_PROMPT,
    _FINAL_SUMMARY_RESPONSE_SCHEMA,
    _FINAL_SUMMARY_SYSTEM_PROMPT,
    _TOPIC_ANALYSIS_RESPONSE_SCHEMA,
    _TOPIC_ANALYSIS_SYSTEM_PROMPT,
    _TOPIC_TIMELINE_RESPONSE_SCHEMA,
    _TOPIC_TIMELINE_SYSTEM_PROMPT,
)
from server.app.services.sessions.workspace_summary_support import (
    _NoteEntry,
    _SummaryChunk,
    _SummaryInputs,
    _TopicAnalysisResult,
    _TopicAnalysisTarget,
    _build_evidence,
    _build_fallback_reduced_topics,
    _build_fallback_summary,
    _build_final_merge_fallback,
    _build_topic_analysis_fallback,
    _build_topic_candidates,
    _build_chunk_topic_fallback,
    _format_ms,
    _format_range,
    _parse_chunk_topic_payload,
    _parse_final_summary_payload,
    _parse_topic_analysis_payload,
    _parse_topic_timeline_payload,
    _ranges_overlap,
    _reduce_meeting_type,
    _select_event_items,
    _select_event_items_in_range,
    _select_topic_candidates_for_range,
)


logger = logging.getLogger(__name__)


class NoOpWorkspaceSummarySynthesizer:
    """요약 생성 기능을 비활성화한다."""

    def synthesize(
        self,
        *,
        session: MeetingSession,
        source_version: int,
        utterances: list[Utterance],
        correction_document: TranscriptCorrectionDocument | None,
        events: list[MeetingEvent],
    ) -> WorkspaceSummaryDocument | None:
        del session, source_version, utterances, correction_document, events
        return None


class LLMWorkspaceSummarySynthesizer:
    """회의 노트를 단계형 map-reduce로 분석해 최종 요약을 만든다."""

    def __init__(
        self,
        completion_client: LLMCompletionClient,
        *,
        model: str,
        note_max_chars: int = 2000,
        chunk_overlap_utterances: int = 2,
        max_chunk_count: int = 12,
    ) -> None:
        self._completion_client = completion_client
        self._model = model
        self._chunk_target_chars = max(note_max_chars, 80)
        self._chunk_overlap_utterances = max(chunk_overlap_utterances, 0)
        self._max_chunk_count = max(max_chunk_count, 1)

    def synthesize(
        self,
        *,
        session: MeetingSession,
        source_version: int,
        utterances: list[Utterance],
        correction_document: TranscriptCorrectionDocument | None,
        events: list[MeetingEvent],
    ) -> WorkspaceSummaryDocument:
        """정리된 노트를 계층형 map-reduce로 요약한다."""

        inputs = self._build_inputs(
            session=session,
            utterances=utterances,
            correction_document=correction_document,
            events=events,
        )
        evidence = _build_evidence(events=events, utterances=utterances)
        base_fallback = _build_fallback_summary(
            session=session,
            source_version=source_version,
            inputs=inputs,
            evidence=evidence,
            model=self._model,
        )
        if not inputs.note_entries:
            return base_fallback

        chunks = self._build_chunks(inputs=inputs, utterances=utterances, events=events)
        if not chunks:
            return base_fallback

        chunk_topic_results = [
            self._analyze_chunk_topics(session=session, chunk=chunk) for chunk in chunks
        ]
        meeting_type, reduced_topics = self._reduce_topic_timeline(
            session=session,
            inputs=inputs,
            chunks=chunks,
            chunk_results=chunk_topic_results,
        )
        if not reduced_topics:
            reduced_topics = _build_fallback_reduced_topics(
                inputs=inputs,
                chunks=chunks,
            )

        topic_targets = self._build_topic_analysis_targets(
            inputs=inputs,
            events=events,
            chunks=chunks,
            reduced_topics=reduced_topics,
            utterances=utterances,
        )
        if not topic_targets:
            return base_fallback

        topic_results = [
            self._analyze_topic(
                session=session,
                meeting_type=meeting_type,
                target=target,
            )
            for target in topic_targets
        ]
        merge_fallback = _build_final_merge_fallback(
            session=session,
            source_version=source_version,
            inputs=inputs,
            meeting_type=meeting_type,
            topic_results=topic_results,
            evidence=evidence,
            model=self._model,
        )

        final_prompt = self._build_final_merge_prompt(
            inputs=inputs,
            meeting_type=meeting_type,
            topic_results=topic_results,
        )
        started_at = time.perf_counter()
        try:
            response_text = self._completion_client.complete(
                final_prompt,
                system_prompt=_FINAL_SUMMARY_SYSTEM_PROMPT,
                response_schema=_FINAL_SUMMARY_RESPONSE_SCHEMA,
                keep_alive="30m",
            )
            payload = json.loads(response_text)
        except Exception:
            elapsed_seconds = time.perf_counter() - started_at
            logger.exception(
                "workspace summary 최종 병합 실패: session_id=%s model=%s topic_count=%s prompt_chars=%s elapsed_seconds=%.3f",
                session.id,
                self._model,
                len(topic_results),
                len(final_prompt),
                elapsed_seconds,
            )
            return merge_fallback

        elapsed_seconds = time.perf_counter() - started_at
        logger.info(
            "workspace summary 합성 완료: session_id=%s model=%s meeting_type=%s chunk_count=%s topic_count=%s prompt_chars=%s elapsed_seconds=%.3f",
            session.id,
            self._model,
            meeting_type,
            len(chunks),
            len(topic_results),
            len(final_prompt),
            elapsed_seconds,
        )
        return _parse_final_summary_payload(
            payload=payload,
            session_id=session.id,
            source_version=source_version,
            model=self._model,
            fallback=merge_fallback,
            topic_results=topic_results,
            evidence=evidence,
        )

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
        note_entries = inputs.note_entries
        if not note_entries:
            return []

        utterance_by_id = {utterance.id: utterance for utterance in utterances}
        chunks: list[_SummaryChunk] = []
        start_index = 0

        while start_index < len(note_entries) and len(chunks) < self._max_chunk_count:
            if len(chunks) == self._max_chunk_count - 1:
                end_index = len(note_entries) - 1
            else:
                end_index = start_index
                total_chars = 0
                while end_index < len(note_entries):
                    line_length = len(note_entries[end_index].rendered) + 1
                    if total_chars > 0 and total_chars + line_length > self._chunk_target_chars:
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
                end_index + 1 - self._chunk_overlap_utterances,
                start_index + 1,
            )

        return chunks

    def _analyze_chunk_topics(
        self,
        *,
        session: MeetingSession,
        chunk: _SummaryChunk,
    ) -> _ChunkTopicResult:
        fallback = _build_chunk_topic_fallback(chunk)
        prompt = self._build_chunk_topic_prompt(chunk)
        started_at = time.perf_counter()
        try:
            response_text = self._completion_client.complete(
                prompt,
                system_prompt=_CHUNK_TOPIC_ANALYSIS_SYSTEM_PROMPT,
                response_schema=_CHUNK_TOPIC_ANALYSIS_RESPONSE_SCHEMA,
                keep_alive="30m",
            )
            payload = json.loads(response_text)
        except Exception:
            elapsed_seconds = time.perf_counter() - started_at
            logger.exception(
                "workspace summary 청크 주제 분석 실패: session_id=%s model=%s chunk_index=%s prompt_chars=%s elapsed_seconds=%.3f",
                session.id,
                self._model,
                chunk.index,
                len(prompt),
                elapsed_seconds,
            )
            return fallback

        elapsed_seconds = time.perf_counter() - started_at
        logger.info(
            "workspace summary 청크 주제 분석 완료: session_id=%s model=%s chunk_index=%s prompt_chars=%s elapsed_seconds=%.3f",
            session.id,
            self._model,
            chunk.index,
            len(prompt),
            elapsed_seconds,
        )
        return _parse_chunk_topic_payload(payload=payload, chunk=chunk, fallback=fallback)

    @staticmethod
    def _build_chunk_topic_prompt(chunk: _SummaryChunk) -> str:
        payload = {
            "구간 번호": chunk.index + 1,
            "구간 시간": _format_range(chunk.start_ms, chunk.end_ms),
            "구간 주제 후보": chunk.topic_candidates,
            "구간 회의 내용": chunk.note_excerpt,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _reduce_topic_timeline(
        self,
        *,
        session: MeetingSession,
        inputs: _SummaryInputs,
        chunks: list[_SummaryChunk],
        chunk_results: list[_ChunkTopicResult],
    ) -> tuple[str, list[_ReducedTopicSegment]]:
        fallback_meeting_type = _reduce_meeting_type(
            [result.meeting_type_vote for result in chunk_results]
        )
        fallback_topics = _build_fallback_reduced_topics(inputs=inputs, chunks=chunks)
        prompt = self._build_topic_timeline_prompt(
            inputs=inputs,
            chunk_results=chunk_results,
        )
        started_at = time.perf_counter()
        try:
            response_text = self._completion_client.complete(
                prompt,
                system_prompt=_TOPIC_TIMELINE_SYSTEM_PROMPT,
                response_schema=_TOPIC_TIMELINE_RESPONSE_SCHEMA,
                keep_alive="30m",
            )
            payload = json.loads(response_text)
        except Exception:
            elapsed_seconds = time.perf_counter() - started_at
            logger.exception(
                "workspace summary 주제 타임라인 병합 실패: session_id=%s model=%s chunk_count=%s prompt_chars=%s elapsed_seconds=%.3f",
                session.id,
                self._model,
                len(chunk_results),
                len(prompt),
                elapsed_seconds,
            )
            return fallback_meeting_type, fallback_topics

        elapsed_seconds = time.perf_counter() - started_at
        logger.info(
            "workspace summary 주제 타임라인 병합 완료: session_id=%s model=%s chunk_count=%s prompt_chars=%s elapsed_seconds=%.3f",
            session.id,
            self._model,
            len(chunk_results),
            len(prompt),
            elapsed_seconds,
        )
        return _parse_topic_timeline_payload(
            payload=payload,
            chunks=chunks,
            fallback_meeting_type=fallback_meeting_type,
            fallback_topics=fallback_topics,
        )

    @staticmethod
    def _build_topic_timeline_prompt(
        *,
        inputs: _SummaryInputs,
        chunk_results: list[_ChunkTopicResult],
    ) -> str:
        payload = {
            "회의 제목": inputs.headline_seed,
            "현재 주제": inputs.current_topic,
            "전역 주제 후보": inputs.topic_candidates,
            "구간별 주제 후보": [
                {
                    "구간 번호": result.index + 1,
                    "구간 시간": _format_range(result.start_ms, result.end_ms),
                    "meeting_type_vote": result.meeting_type_vote,
                    "chunk_summary": result.chunk_summary,
                    "local_topics": [
                        {"title": topic.title, "summary": topic.summary}
                        for topic in result.local_topics
                    ],
                }
                for result in chunk_results
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

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

    def _analyze_topic(
        self,
        *,
        session: MeetingSession,
        meeting_type: str,
        target: _TopicAnalysisTarget,
    ) -> _TopicAnalysisResult:
        fallback = _build_topic_analysis_fallback(target)
        prompt = self._build_topic_analysis_prompt(
            meeting_type=meeting_type,
            target=target,
        )
        started_at = time.perf_counter()
        try:
            response_text = self._completion_client.complete(
                prompt,
                system_prompt=_TOPIC_ANALYSIS_SYSTEM_PROMPT,
                response_schema=_TOPIC_ANALYSIS_RESPONSE_SCHEMA,
                keep_alive="30m",
            )
            payload = json.loads(response_text)
        except Exception:
            elapsed_seconds = time.perf_counter() - started_at
            logger.exception(
                "workspace summary 주제별 분석 실패: session_id=%s model=%s topic_index=%s prompt_chars=%s elapsed_seconds=%.3f",
                session.id,
                self._model,
                target.source_index,
                len(prompt),
                elapsed_seconds,
            )
            return fallback

        elapsed_seconds = time.perf_counter() - started_at
        logger.info(
            "workspace summary 주제별 분석 완료: session_id=%s model=%s topic_index=%s prompt_chars=%s elapsed_seconds=%.3f",
            session.id,
            self._model,
            target.source_index,
            len(prompt),
            elapsed_seconds,
        )
        return _parse_topic_analysis_payload(
            payload=payload,
            target=target,
            fallback=fallback,
        )

    @staticmethod
    def _build_topic_analysis_prompt(
        *,
        meeting_type: str,
        target: _TopicAnalysisTarget,
    ) -> str:
        payload = {
            "meeting_type": meeting_type,
            "주제 번호": target.source_index + 1,
            "주제 제목": target.title,
            "주제 시간": _format_range(target.start_ms, target.end_ms),
            "주제 결정 후보": target.decisions,
            "주제 후속 작업 후보": target.next_actions,
            "주제 남은 질문 후보": target.open_questions,
            "주제 회의 내용": target.note_excerpt,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _build_final_merge_prompt(
        *,
        inputs: _SummaryInputs,
        meeting_type: str,
        topic_results: list[_TopicAnalysisResult],
    ) -> str:
        payload = {
            "meeting_type": meeting_type,
            "회의 제목": inputs.headline_seed,
            "현재 주제": inputs.current_topic,
            "전역 결정 후보": inputs.decisions,
            "전역 후속 작업 후보": inputs.next_actions,
            "전역 남은 질문 후보": inputs.open_questions,
            "주제별 분석 결과": [
                {
                    "주제 번호": result.source_index + 1,
                    "주제 제목": result.title,
                    "주제 시간": _format_range(result.start_ms, result.end_ms),
                    "summary": result.summary,
                    "decisions": result.decisions,
                    "next_actions": [
                        {
                            "title": item.title,
                            "owner": item.owner,
                            "due_date": item.due_date,
                        }
                        for item in result.next_actions
                    ],
                    "open_questions": result.open_questions,
                }
                for result in topic_results
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)
