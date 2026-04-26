"""정제 없이 원본 회의록을 그대로 반환하는 리파이너."""

from __future__ import annotations

from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)


class NoOpReportRefiner(ReportRefiner):
    """LLM이 없을 때 원본 Markdown을 그대로 돌려준다."""

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        return refinement_input.raw_markdown
