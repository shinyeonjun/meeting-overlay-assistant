"""workspace summary LLM payload 파싱 함수."""

from __future__ import annotations

from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryDocument,
    WorkspaceSummaryEvidence,
    WorkspaceSummaryTopic,
)
from server.app.services.sessions.workspace_summary_types import (
    _ChunkTopicResult,
    _ReducedTopicSegment,
    _SummaryChunk,
    _TopicAnalysisResult,
    _TopicAnalysisTarget,
)
from server.app.services.sessions.workspace_summary_utils import (
    _clean_action_items,
    _clean_chunk_topics,
    _clean_int_list,
    _clean_string_list,
    _looks_like_raw_transcript,
    _normalize_meeting_type,
)


def _parse_final_summary_payload(
    *,
    payload: dict[str, object],
    session_id: str,
    source_version: int,
    model: str,
    fallback: WorkspaceSummaryDocument,
    topic_results: list[_TopicAnalysisResult],
    evidence: list[WorkspaceSummaryEvidence],
) -> WorkspaceSummaryDocument:
    headline = str(payload.get("headline") or "").strip() or fallback.headline
    summary = (
        _clean_string_list(payload.get("summary"), limit=4, max_chars=180)
        or fallback.summary
    )
    decisions = (
        _clean_string_list(payload.get("decisions"), limit=3, max_chars=90)
        or fallback.decisions
    )
    next_actions = (
        _clean_action_items(payload.get("next_actions"), limit=3, max_chars=80)
        or fallback.next_actions
    )
    open_questions = (
        _clean_string_list(payload.get("open_questions"), limit=2, max_chars=90)
        or fallback.open_questions
    )
    changed_since_last_meeting = _clean_string_list(
        payload.get("changed_since_last_meeting"),
        limit=2,
        max_chars=90,
    )
    topics = [
        WorkspaceSummaryTopic(
            title=result.title,
            summary=result.summary,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
        )
        for result in topic_results[:4]
    ]
    return WorkspaceSummaryDocument(
        session_id=session_id,
        source_version=source_version,
        model=model,
        headline=headline,
        summary=summary,
        topics=topics or fallback.topics,
        decisions=decisions,
        next_actions=next_actions,
        open_questions=open_questions,
        changed_since_last_meeting=changed_since_last_meeting,
        evidence=evidence or fallback.evidence,
    )


def _parse_chunk_topic_payload(
    *,
    payload: dict[str, object],
    chunk: _SummaryChunk,
    fallback: _ChunkTopicResult,
) -> _ChunkTopicResult:
    meeting_type_vote = _normalize_meeting_type(
        payload.get("meeting_type"),
        fallback.meeting_type_vote,
    )
    chunk_summary = (
        _clean_string_list(payload.get("chunk_summary"), limit=2, max_chars=160)
        or fallback.chunk_summary
    )
    local_topics = _clean_chunk_topics(
        payload.get("local_topics"),
        fallback=fallback.local_topics,
        limit=2,
    )
    return _ChunkTopicResult(
        index=chunk.index,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        meeting_type_vote=meeting_type_vote,
        chunk_summary=chunk_summary,
        local_topics=local_topics,
    )


def _parse_topic_timeline_payload(
    *,
    payload: dict[str, object],
    chunks: list[_SummaryChunk],
    fallback_meeting_type: str,
    fallback_topics: list[_ReducedTopicSegment],
) -> tuple[str, list[_ReducedTopicSegment]]:
    meeting_type = _normalize_meeting_type(
        payload.get("meeting_type"),
        fallback_meeting_type,
    )
    raw_topics = payload.get("topics")
    if not isinstance(raw_topics, list):
        return meeting_type, fallback_topics

    topics: list[_ReducedTopicSegment] = []
    seen_chunks: set[tuple[int, ...]] = set()
    for raw_topic in raw_topics:
        if not isinstance(raw_topic, dict):
            continue
        chunk_indexes = _clean_int_list(
            raw_topic.get("chunk_indexes"),
            allowed_values=set(range(len(chunks))),
            limit=8,
        )
        chunk_key = tuple(chunk_indexes)
        if not chunk_indexes or chunk_key in seen_chunks:
            continue
        title = str(raw_topic.get("title") or "").strip()
        summary = str(raw_topic.get("summary") or "").strip()
        if not title or not summary or _looks_like_raw_transcript(summary):
            continue
        start_ms = min(chunks[index].start_ms for index in chunk_indexes)
        end_ms = max(chunks[index].end_ms for index in chunk_indexes)
        topics.append(
            _ReducedTopicSegment(
                source_index=len(topics),
                title=title,
                summary=summary,
                start_ms=start_ms,
                end_ms=end_ms,
                chunk_indexes=chunk_indexes,
            )
        )
        seen_chunks.add(chunk_key)
        if len(topics) >= 5:
            break
    return meeting_type, topics or fallback_topics


def _parse_topic_analysis_payload(
    *,
    payload: dict[str, object],
    target: _TopicAnalysisTarget,
    fallback: _TopicAnalysisResult,
) -> _TopicAnalysisResult:
    summary_text = str(payload.get("summary") or "").strip()
    if not summary_text or _looks_like_raw_transcript(summary_text):
        summary_text = fallback.summary
    return _TopicAnalysisResult(
        source_index=target.source_index,
        title=target.title,
        summary=summary_text,
        start_ms=target.start_ms,
        end_ms=target.end_ms,
        chunk_indexes=target.chunk_indexes,
        decisions=(
            _clean_string_list(payload.get("decisions"), limit=3, max_chars=90)
            or fallback.decisions
        ),
        next_actions=(
            _clean_action_items(payload.get("next_actions"), limit=3, max_chars=80)
            or fallback.next_actions
        ),
        open_questions=(
            _clean_string_list(payload.get("open_questions"), limit=2, max_chars=90)
            or fallback.open_questions
        ),
    )
