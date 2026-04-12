"""LLM 분석 입출력 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMAnalysisInput:
    """LLM 분석에 전달할 입력."""

    session_id: str
    utterance_id: str
    text: str


@dataclass(frozen=True)
class LLMEventCandidate:
    """LLM이 반환하는 이벤트 후보."""

    event_type: str
    title: str
    state: str
    priority: int
    body: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    topic_group: str | None = None


@dataclass(frozen=True)
class LLMAnalysisResult:
    """LLM 분석 결과."""

    candidates: list[LLMEventCandidate] = field(default_factory=list)
