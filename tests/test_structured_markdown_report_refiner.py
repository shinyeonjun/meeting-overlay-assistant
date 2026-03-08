from __future__ import annotations

from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
)
from backend.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class TestStructuredMarkdownReportRefiner:
    def test_이벤트_메타데이터를_읽기좋은_섹션으로_재구성한다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-1",
                raw_markdown="# raw",
                events=[
                    ReportRefinementEvent(
                        event_type="decision",
                        title="출시는 3월 14일로 확정한다.",
                        state="confirmed",
                        priority=85,
                        evidence_text="이번 주 금요일에 출시합시다.",
                    ),
                    ReportRefinementEvent(
                        event_type="action_item",
                        title="민수가 배포 체크리스트를 정리한다.",
                        state="open",
                        priority=90,
                        assignee="민수",
                        due_date="2026-03-14",
                    ),
                    ReportRefinementEvent(
                        event_type="risk",
                        title="QA 시간이 부족할 수 있다.",
                        state="open",
                        priority=80,
                    ),
                ],
                speaker_transcript_lines=[
                    "[SPEAKER_00] (0ms-1200ms, confidence=0.910) 이번 주 금요일에 출시합시다."
                ],
                speaker_event_lines=[
                    "[decision] SPEAKER_00: 출시는 3월 14일로 확정한다."
                ],
            )
        )

        assert result.startswith("# Session Report: session-1")
        assert "## Snapshot" in result
        assert "- Total events: 3" in result
        assert "## Decisions" in result
        assert "1. 출시는 3월 14일로 확정한다." in result
        assert "## Action Items" in result
        assert "- [ ] 민수가 배포 체크리스트를 정리한다. (민수)" in result
        assert "  - due_date: 2026-03-14" in result
        assert "## Risks" in result
        assert "## Speaker Notes" in result
        assert "## Speaker-attributed Events" in result

    def test_이벤트가_없으면_빈_섹션을_없음으로_채운다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-empty",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# Session Report: session-empty")
        assert result.count("- 없음") >= 6
