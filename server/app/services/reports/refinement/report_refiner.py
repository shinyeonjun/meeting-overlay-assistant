"""리포트 영역의 report refiner 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ReportRefinementEvent:
    """리포트 정제에 필요한 이벤트 요약 모델."""

    event_type: str
    title: str
    state: str
    evidence_text: str | None = None
    speaker_label: str | None = None
    input_source: str | None = None


@dataclass(frozen=True)
class ReportRefinementInput:
    """리포트 정제에 필요한 입력."""

    session_id: str
    raw_markdown: str
    events: list[ReportRefinementEvent] = field(default_factory=list)
    event_lines: list[str] = field(default_factory=list)
    speaker_transcript_lines: list[str] = field(default_factory=list)
    speaker_event_lines: list[str] = field(default_factory=list)


class ReportRefiner(Protocol):
    """회의 리포트를 읽기 좋은 결과로 정제하는 서비스 인터페이스."""

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        """입력 리포트를 더 읽기 좋은 결과로 정제한다."""
