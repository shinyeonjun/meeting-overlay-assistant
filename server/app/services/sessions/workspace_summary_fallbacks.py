"""workspace summary fallback 문서 생성 함수."""

from __future__ import annotations

from server.app.domain.session import MeetingSession
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryActionItem,
    WorkspaceSummaryDocument,
    WorkspaceSummaryEvidence,
    WorkspaceSummaryTopic,
)
from server.app.services.sessions.workspace_summary_types import (
    _ChunkTopicCandidate,
    _ChunkTopicResult,
    _ReducedTopicSegment,
    _SummaryChunk,
    _SummaryInputs,
    _TopicAnalysisResult,
    _TopicAnalysisTarget,
)
from server.app.services.sessions.workspace_summary_utils import (
    _dedupe_action_items,
    _dedupe_strings,
    _ranges_overlap,
)


def _build_fallback_summary(
    *,
    session: MeetingSession,
    source_version: int,
    inputs: _SummaryInputs,
    evidence: list[WorkspaceSummaryEvidence],
    model: str,
) -> WorkspaceSummaryDocument:
    fallback_topics = [
        WorkspaceSummaryTopic(
            title=str(item["title"]),
            summary=f"{item['title']} 관련 논의를 이어갔습니다.",
            start_ms=int(item["start_ms"]),
            end_ms=int(item["end_ms"]),
        )
        for item in inputs.topic_candidates[:4]
    ]

    summary: list[str] = []
    if fallback_topics:
        joined_titles = ", ".join(topic.title for topic in fallback_topics[:3])
        summary.append(f"이번 회의에서는 {joined_titles} 등을 중심으로 논의했습니다.")
    elif inputs.current_topic:
        summary.append(f"이번 회의에서는 {inputs.current_topic}를 중심으로 논의했습니다.")
    if inputs.decisions:
        summary.append(f"정리된 결정 후보로는 {inputs.decisions[0]['title']}가 보입니다.")
    if inputs.next_actions:
        summary.append(f"바로 이어서 할 일 후보로는 {inputs.next_actions[0]['title']}가 있습니다.")
    elif inputs.open_questions:
        summary.append(f"남은 쟁점으로는 {inputs.open_questions[0]['title']}가 있습니다.")
    if not summary:
        summary.append("회의 내용을 바탕으로 핵심 요약을 정리하는 중입니다.")

    return WorkspaceSummaryDocument(
        session_id=session.id,
        source_version=source_version,
        model=model,
        headline=inputs.headline_seed or session.title,
        summary=summary[:4],
        topics=fallback_topics,
        decisions=[item["title"] for item in inputs.decisions[:3]],
        next_actions=[
            WorkspaceSummaryActionItem(
                title=item["title"],
                owner=item["speaker_label"],
            )
            for item in inputs.next_actions[:3]
        ],
        open_questions=[item["title"] for item in inputs.open_questions[:2]],
        changed_since_last_meeting=[],
        evidence=evidence,
    )


def _build_chunk_topic_fallback(chunk: _SummaryChunk) -> _ChunkTopicResult:
    local_topics = [
        _ChunkTopicCandidate(
            title=str(item["title"]),
            summary=f"{item['title']} 관련 대화가 이어졌습니다.",
        )
        for item in chunk.topic_candidates[:2]
    ]
    chunk_summary = (
        [f"{local_topics[0].title} 관련 내용을 확인했습니다."]
        if local_topics
        else ["이 구간에서는 보조 대화나 분위기성 발화가 이어졌습니다."]
    )
    return _ChunkTopicResult(
        index=chunk.index,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        meeting_type_vote="business_meeting",
        chunk_summary=chunk_summary,
        local_topics=local_topics,
    )


def _build_fallback_reduced_topics(
    *,
    inputs: _SummaryInputs,
    chunks: list[_SummaryChunk],
) -> list[_ReducedTopicSegment]:
    if inputs.topic_candidates:
        return [
            _ReducedTopicSegment(
                source_index=index,
                title=str(item["title"]),
                summary=f"{item['title']} 관련 논의를 이어갔습니다.",
                start_ms=int(item["start_ms"]),
                end_ms=int(item["end_ms"]),
                chunk_indexes=[
                    chunk.index
                    for chunk in chunks
                    if _ranges_overlap(
                        int(item["start_ms"]),
                        int(item["end_ms"]),
                        chunk.start_ms,
                        chunk.end_ms,
                    )
                ]
                or [0],
            )
            for index, item in enumerate(inputs.topic_candidates[:4])
        ]

    return [
        _ReducedTopicSegment(
            source_index=0,
            title=inputs.current_topic or inputs.headline_seed,
            summary="회의 전체 논의를 한 주제로 정리했습니다.",
            start_ms=chunks[0].start_ms,
            end_ms=chunks[-1].end_ms,
            chunk_indexes=[chunk.index for chunk in chunks],
        )
    ]


def _build_topic_analysis_fallback(target: _TopicAnalysisTarget) -> _TopicAnalysisResult:
    if target.decisions or target.next_actions or target.open_questions:
        summary = f"{target.title} 주제에서 후속 판단이 필요한 논의가 이어졌습니다."
    else:
        summary = f"{target.title} 주제에 대한 논의가 이어졌습니다."
    return _TopicAnalysisResult(
        source_index=target.source_index,
        title=target.title,
        summary=summary,
        start_ms=target.start_ms,
        end_ms=target.end_ms,
        chunk_indexes=target.chunk_indexes,
        decisions=[item["title"] for item in target.decisions[:3]],
        next_actions=[
            WorkspaceSummaryActionItem(
                title=item["title"],
                owner=item["speaker_label"],
            )
            for item in target.next_actions[:3]
        ],
        open_questions=[item["title"] for item in target.open_questions[:2]],
    )


def _build_final_merge_fallback(
    *,
    session: MeetingSession,
    source_version: int,
    inputs: _SummaryInputs,
    meeting_type: str,
    topic_results: list[_TopicAnalysisResult],
    evidence: list[WorkspaceSummaryEvidence],
    model: str,
) -> WorkspaceSummaryDocument:
    del meeting_type
    topics = [
        WorkspaceSummaryTopic(
            title=result.title,
            summary=result.summary,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
        )
        for result in topic_results[:4]
    ]
    summary = _dedupe_strings(
        [result.summary for result in topic_results if result.summary],
        limit=4,
    )
    if not summary:
        joined_titles = ", ".join(topic.title for topic in topics[:3])
        summary = [f"이번 회의에서는 {joined_titles} 등을 중심으로 논의했습니다."]
    return WorkspaceSummaryDocument(
        session_id=session.id,
        source_version=source_version,
        model=model,
        headline=inputs.headline_seed or session.title,
        summary=summary,
        topics=topics,
        decisions=_dedupe_strings(
            [item for result in topic_results for item in result.decisions],
            limit=3,
        ),
        next_actions=_dedupe_action_items(
            [item for result in topic_results for item in result.next_actions],
            limit=3,
        ),
        open_questions=_dedupe_strings(
            [item for result in topic_results for item in result.open_questions],
            limit=2,
        ),
        changed_since_last_meeting=[],
        evidence=evidence,
    )
