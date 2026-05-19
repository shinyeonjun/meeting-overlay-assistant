"""워크스페이스 회의 노트 요약 synthesizer."""

from __future__ import annotations

import logging

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.refinement import TranscriptCorrectionDocument
from server.app.services.sessions.workspace_summary_models import WorkspaceSummaryDocument
from server.app.services.sessions.workspace_summary_models import WorkspaceSummaryEvidence
from server.app.services.sessions.workspace_summary_prompt_builder import (
    build_chunk_topic_prompt,
    build_final_merge_prompt,
    build_topic_analysis_prompt,
    build_topic_timeline_prompt,
)
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
from server.app.services.sessions.workspace_summary_input_builder import (
    WorkspaceSummaryInputBuilderMixin,
)
from server.app.services.sessions.workspace_summary_completion import (
    complete_workspace_summary_json_payload,
)
from server.app.services.sessions.workspace_summary_fallbacks import (
    _build_chunk_topic_fallback,
    _build_fallback_reduced_topics,
    _build_fallback_summary,
    _build_final_merge_fallback,
    _build_topic_analysis_fallback,
)
from server.app.services.sessions.workspace_summary_payload_parser import (
    _parse_chunk_topic_payload,
    _parse_final_summary_payload,
    _parse_topic_analysis_payload,
    _parse_topic_timeline_payload,
)
from server.app.services.sessions.workspace_summary_selection import (
    _build_evidence,
)
from server.app.services.sessions.workspace_summary_types import (
    _SummaryChunk,
    _SummaryInputs,
    _TopicAnalysisResult,
    _ChunkTopicResult,
    _ReducedTopicSegment,
    _TopicAnalysisTarget,
)
from server.app.services.sessions.workspace_summary_utils import (
    _reduce_meeting_type,
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


class LLMWorkspaceSummarySynthesizer(WorkspaceSummaryInputBuilderMixin):
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
        base_fallback, evidence = self._build_base_fallback(
            session=session,
            source_version=source_version,
            inputs=inputs,
            utterances=utterances,
            events=events,
        )
        if not inputs.note_entries:
            return base_fallback

        chunks = self._build_chunks(inputs=inputs, utterances=utterances, events=events)
        if not chunks:
            return base_fallback

        chunk_topic_results = self._analyze_chunk_topic_results(
            session=session,
            chunks=chunks,
        )
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

        topic_results = self._analyze_topic_results(
            session=session,
            meeting_type=meeting_type,
            topic_targets=topic_targets,
        )
        return self._merge_final_summary(
            session=session,
            source_version=source_version,
            inputs=inputs,
            chunks=chunks,
            meeting_type=meeting_type,
            topic_results=topic_results,
            evidence=evidence,
        )

    def _build_base_fallback(
        self,
        *,
        session: MeetingSession,
        source_version: int,
        inputs: _SummaryInputs,
        utterances: list[Utterance],
        events: list[MeetingEvent],
    ) -> tuple[WorkspaceSummaryDocument, list[WorkspaceSummaryEvidence]]:
        evidence = _build_evidence(events=events, utterances=utterances)
        return (
            _build_fallback_summary(
                session=session,
                source_version=source_version,
                inputs=inputs,
                evidence=evidence,
                model=self._model,
            ),
            evidence,
        )

    def _analyze_chunk_topic_results(
        self,
        *,
        session: MeetingSession,
        chunks: list[_SummaryChunk],
    ) -> list[_ChunkTopicResult]:
        return [
            self._analyze_chunk_topics(session=session, chunk=chunk) for chunk in chunks
        ]

    def _analyze_topic_results(
        self,
        *,
        session: MeetingSession,
        meeting_type: str,
        topic_targets: list[_TopicAnalysisTarget],
    ) -> list[_TopicAnalysisResult]:
        return [
            self._analyze_topic(
                session=session,
                meeting_type=meeting_type,
                target=target,
            )
            for target in topic_targets
        ]

    def _merge_final_summary(
        self,
        *,
        session: MeetingSession,
        source_version: int,
        inputs: _SummaryInputs,
        chunks: list[_SummaryChunk],
        meeting_type: str,
        topic_results: list[_TopicAnalysisResult],
        evidence: list[WorkspaceSummaryEvidence],
    ) -> WorkspaceSummaryDocument:
        merge_fallback = _build_final_merge_fallback(
            session=session,
            source_version=source_version,
            inputs=inputs,
            meeting_type=meeting_type,
            topic_results=topic_results,
            evidence=evidence,
            model=self._model,
        )

        final_prompt = build_final_merge_prompt(
            inputs=inputs,
            meeting_type=meeting_type,
            topic_results=topic_results,
        )
        payload = self._complete_json_payload(
            prompt=final_prompt,
            system_prompt=_FINAL_SUMMARY_SYSTEM_PROMPT,
            response_schema=_FINAL_SUMMARY_RESPONSE_SCHEMA,
            failure_message="workspace summary 최종 병합 실패: session_id=%s model=%s topic_count=%s prompt_chars=%s elapsed_seconds=%.3f",
            success_message="workspace summary 합성 완료: session_id=%s model=%s meeting_type=%s chunk_count=%s topic_count=%s prompt_chars=%s elapsed_seconds=%.3f",
            failure_args=(session.id, self._model, len(topic_results)),
            success_args=(
                session.id,
                self._model,
                meeting_type,
                len(chunks),
                len(topic_results),
            ),
        )
        if payload is None:
            return merge_fallback

        return _parse_final_summary_payload(
            payload=payload,
            session_id=session.id,
            source_version=source_version,
            model=self._model,
            fallback=merge_fallback,
            topic_results=topic_results,
            evidence=evidence,
        )

    def _analyze_chunk_topics(
        self,
        *,
        session: MeetingSession,
        chunk: _SummaryChunk,
    ) -> _ChunkTopicResult:
        fallback = _build_chunk_topic_fallback(chunk)
        prompt = build_chunk_topic_prompt(chunk)
        payload = self._complete_json_payload(
            prompt=prompt,
            system_prompt=_CHUNK_TOPIC_ANALYSIS_SYSTEM_PROMPT,
            response_schema=_CHUNK_TOPIC_ANALYSIS_RESPONSE_SCHEMA,
            failure_message="workspace summary 청크 주제 분석 실패: session_id=%s model=%s chunk_index=%s prompt_chars=%s elapsed_seconds=%.3f",
            success_message="workspace summary 청크 주제 분석 완료: session_id=%s model=%s chunk_index=%s prompt_chars=%s elapsed_seconds=%.3f",
            failure_args=(session.id, self._model, chunk.index),
            success_args=(session.id, self._model, chunk.index),
        )
        if payload is None:
            return fallback

        return _parse_chunk_topic_payload(payload=payload, chunk=chunk, fallback=fallback)

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
        prompt = build_topic_timeline_prompt(
            inputs=inputs,
            chunk_results=chunk_results,
        )
        payload = self._complete_json_payload(
            prompt=prompt,
            system_prompt=_TOPIC_TIMELINE_SYSTEM_PROMPT,
            response_schema=_TOPIC_TIMELINE_RESPONSE_SCHEMA,
            failure_message="workspace summary 주제 타임라인 병합 실패: session_id=%s model=%s chunk_count=%s prompt_chars=%s elapsed_seconds=%.3f",
            success_message="workspace summary 주제 타임라인 병합 완료: session_id=%s model=%s chunk_count=%s prompt_chars=%s elapsed_seconds=%.3f",
            failure_args=(session.id, self._model, len(chunk_results)),
            success_args=(session.id, self._model, len(chunk_results)),
        )
        if payload is None:
            return fallback_meeting_type, fallback_topics

        return _parse_topic_timeline_payload(
            payload=payload,
            chunks=chunks,
            fallback_meeting_type=fallback_meeting_type,
            fallback_topics=fallback_topics,
        )

    def _analyze_topic(
        self,
        *,
        session: MeetingSession,
        meeting_type: str,
        target: _TopicAnalysisTarget,
    ) -> _TopicAnalysisResult:
        fallback = _build_topic_analysis_fallback(target)
        prompt = build_topic_analysis_prompt(
            meeting_type=meeting_type,
            target=target,
        )
        payload = self._complete_json_payload(
            prompt=prompt,
            system_prompt=_TOPIC_ANALYSIS_SYSTEM_PROMPT,
            response_schema=_TOPIC_ANALYSIS_RESPONSE_SCHEMA,
            failure_message="workspace summary 주제별 분석 실패: session_id=%s model=%s topic_index=%s prompt_chars=%s elapsed_seconds=%.3f",
            success_message="workspace summary 주제별 분석 완료: session_id=%s model=%s topic_index=%s prompt_chars=%s elapsed_seconds=%.3f",
            failure_args=(session.id, self._model, target.source_index),
            success_args=(session.id, self._model, target.source_index),
        )
        if payload is None:
            return fallback

        return _parse_topic_analysis_payload(
            payload=payload,
            target=target,
            fallback=fallback,
        )

    def _complete_json_payload(
        self,
        *,
        prompt: str,
        system_prompt: str,
        response_schema: dict[str, object],
        failure_message: str,
        success_message: str,
        failure_args: tuple[object, ...],
        success_args: tuple[object, ...],
    ) -> dict[str, object] | None:
        return complete_workspace_summary_json_payload(
            completion_client=self._completion_client,
            logger=logger,
            prompt=prompt,
            system_prompt=system_prompt,
            response_schema=response_schema,
            failure_message=failure_message,
            success_message=success_message,
            failure_args=failure_args,
            success_args=success_args,
        )
