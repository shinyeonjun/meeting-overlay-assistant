"""workspace summary LLM 단계별 prompt payload를 만든다."""

from __future__ import annotations

import json

from server.app.services.sessions.workspace_summary_types import (
    _ChunkTopicResult,
    _SummaryChunk,
    _SummaryInputs,
    _TopicAnalysisResult,
    _TopicAnalysisTarget,
)
from server.app.services.sessions.workspace_summary_utils import _format_range


def build_chunk_topic_prompt(chunk: _SummaryChunk) -> str:
    payload = {
        "구간 번호": chunk.index + 1,
        "구간 시간": _format_range(chunk.start_ms, chunk.end_ms),
        "구간 주제 후보": chunk.topic_candidates,
        "구간 회의 내용": chunk.note_excerpt,
    }
    return _dump_prompt_payload(payload)


def build_topic_timeline_prompt(
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
    return _dump_prompt_payload(payload)


def build_topic_analysis_prompt(
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
    return _dump_prompt_payload(payload)


def build_final_merge_prompt(
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
    return _dump_prompt_payload(payload)


def _dump_prompt_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
