"""워크스페이스 우측 패널용 요약 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkspaceSummaryActionItem:
    """우측 패널에 노출할 후속 작업 한 건."""

    title: str
    owner: str | None = None
    due_date: str | None = None


@dataclass(frozen=True)
class WorkspaceSummaryEvidence:
    """요약 항목과 연결할 근거 구간."""

    label: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class WorkspaceSummaryTopic:
    """회의 안에서 다뤄진 주제 흐름 한 구간."""

    title: str
    summary: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class WorkspaceSummaryDocument:
    """세션 기준 사람용 업무 요약 문서."""

    session_id: str
    source_version: int
    model: str
    headline: str
    summary: list[str] = field(default_factory=list)
    topics: list[WorkspaceSummaryTopic] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    next_actions: list[WorkspaceSummaryActionItem] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    changed_since_last_meeting: list[str] = field(default_factory=list)
    evidence: list[WorkspaceSummaryEvidence] = field(default_factory=list)
