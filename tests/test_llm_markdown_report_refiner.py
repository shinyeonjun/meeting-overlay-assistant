from __future__ import annotations

from backend.app.services.reports.refinement.llm_markdown_report_refiner import (
    LLMMarkdownReportRefiner,
)
from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
)


class FakeCompletionClient:
    def __init__(self, response_text: str, should_raise: bool = False) -> None:
        self._response_text = response_text
        self._should_raise = should_raise

    def complete(self, prompt: str) -> str:
        if self._should_raise:
            raise RuntimeError("boom")
        return self._response_text


class TestLLMMarkdownReportRefiner:
    def test_llm_응답이_있으면_정제된_markdown을_반환한다(self):
        refiner = LLMMarkdownReportRefiner(
            FakeCompletionClient("# Session Report: s\n\n## Snapshot\n- 정리됨")
        )

        result = refiner.refine(
            ReportRefinementInput(
                session_id="s",
                raw_markdown="# raw",
                event_lines=["[question] 이거 맞아요?"],
            )
        )

        assert result.startswith("# Session Report: s")
        assert "- 정리됨" in result

    def test_llm_실패시_raw_markdown으로_fallback한다(self):
        refiner = LLMMarkdownReportRefiner(FakeCompletionClient("", should_raise=True))

        result = refiner.refine(
            ReportRefinementInput(
                session_id="s",
                raw_markdown="# raw",
            )
        )

        assert result == "# raw"
