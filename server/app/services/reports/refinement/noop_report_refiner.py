"""리포트 영역의 noop report refiner 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)


class NoOpReportRefiner(ReportRefiner):
    """LLM이 없을 때 원본 Markdown을 그대로 돌려준다."""

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        return refinement_input.raw_markdown
