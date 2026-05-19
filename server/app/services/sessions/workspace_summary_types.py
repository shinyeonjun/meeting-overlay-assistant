"""workspace summary 분석 단계에서 공유하는 내부 타입."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryActionItem,
)


@dataclass(frozen=True)
class _NoteEntry:
    utterance_id: str
    start_ms: int
    end_ms: int
    rendered: str


@dataclass(frozen=True)
class _SummaryInputs:
    headline_seed: str
    note_entries: list[_NoteEntry]
    current_topic: str | None
    topic_candidates: list[dict[str, int | str]]
    decisions: list[dict[str, str | None]]
    next_actions: list[dict[str, str | None]]
    open_questions: list[dict[str, str | None]]


@dataclass(frozen=True)
class _SummaryChunk:
    index: int
    start_ms: int
    end_ms: int
    note_excerpt: str
    topic_candidates: list[dict[str, int | str]]
    decisions: list[dict[str, str | None]]
    next_actions: list[dict[str, str | None]]
    open_questions: list[dict[str, str | None]]


@dataclass(frozen=True)
class _ChunkTopicCandidate:
    title: str
    summary: str


@dataclass(frozen=True)
class _ChunkTopicResult:
    index: int
    start_ms: int
    end_ms: int
    meeting_type_vote: str
    chunk_summary: list[str]
    local_topics: list[_ChunkTopicCandidate]


@dataclass(frozen=True)
class _ReducedTopicSegment:
    source_index: int
    title: str
    summary: str
    start_ms: int
    end_ms: int
    chunk_indexes: list[int]


@dataclass(frozen=True)
class _TopicAnalysisTarget:
    source_index: int
    title: str
    start_ms: int
    end_ms: int
    chunk_indexes: list[int]
    note_excerpt: str
    decisions: list[dict[str, str | None]]
    next_actions: list[dict[str, str | None]]
    open_questions: list[dict[str, str | None]]


@dataclass(frozen=True)
class _TopicAnalysisResult:
    source_index: int
    title: str
    summary: str
    start_ms: int
    end_ms: int
    chunk_indexes: list[int]
    decisions: list[str]
    next_actions: list[WorkspaceSummaryActionItem]
    open_questions: list[str]
