from __future__ import annotations

from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
)
from backend.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class TestStructuredMarkdownReportRefiner:
    def test_이벤트_메타데이터를_사용자용_섹션으로_구성한다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-1",
                raw_markdown="# raw",
                events=[
                    ReportRefinementEvent(
                        event_type="decision",
                        title="출시를 3월 14일로 확정한다.",
                        state="confirmed",
                        priority=85,
                        evidence_text="이번 주 금요일에 출시합시다.",
                    ),
                    ReportRefinementEvent(
                        event_type="action_item",
                        title="민수가 발표 체크리스트를 정리한다.",
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
                    "[decision] SPEAKER_00: 출시를 3월 14일로 확정한다."
                ],
            )
        )

        assert result.startswith("# 회의 리포트")
        assert "- 세션 ID: session-1" in result
        assert "## 회의 개요" in result
        assert "- 추출 이벤트: 3건" in result
        assert "## 결정 사항" in result
        assert "1. 출시를 3월 14일로 확정한다." in result
        assert "## 액션 아이템" in result
        assert "- [ ] 민수가 발표 체크리스트를 정리한다. (민수)" in result
        assert "  - 기한: 2026-03-14" in result
        assert "## 리스크" in result
        assert "## 참고 전사" in result
        assert "## 발화자 기반 인사이트" in result

    def test_이벤트가_없으면_빈_섹션을_없음으로_채운다(self):
        refiner = StructuredMarkdownReportRefiner()

        result = refiner.refine(
            ReportRefinementInput(
                session_id="session-empty",
                raw_markdown="# raw",
            )
        )

        assert result.startswith("# 회의 리포트")
        assert result.count("- 없음") >= 6
