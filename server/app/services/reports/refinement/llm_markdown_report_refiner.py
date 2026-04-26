"""LLM 기반 Markdown 회의록 정제기."""

from __future__ import annotations

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.refinement.llm_helpers.markdown_postprocess import (
    looks_like_markdown_report,
    normalize_markdown_headings,
    normalize_section_bullets,
    repair_markdown_report,
)
from server.app.services.reports.refinement.llm_helpers.prompt_builder import (
    build_refinement_prompt,
)
from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class LLMMarkdownReportRefiner(ReportRefiner):
    """LLM 응답을 표준 Markdown 회의록 형식으로 보정한다."""

    def __init__(self, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client
        self._fallback_refiner = StructuredMarkdownReportRefiner()

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        fallback_markdown = self._fallback_refiner.refine(refinement_input)
        prompt = self._build_prompt(refinement_input)
        try:
            refined_markdown = self._completion_client.complete(prompt).strip()
        except Exception:
            return fallback_markdown

        if not refined_markdown:
            return fallback_markdown

        normalized_markdown = self._normalize_markdown_headings(refined_markdown)
        if not self._looks_like_markdown_report(normalized_markdown):
            return fallback_markdown

        normalized_bullets = self._normalize_section_bullets(normalized_markdown)
        return self._repair_markdown_report(normalized_bullets, fallback_markdown)

    def _build_prompt(self, refinement_input: ReportRefinementInput) -> str:
        return build_refinement_prompt(refinement_input)

    @staticmethod
    def _looks_like_markdown_report(content: str) -> bool:
        return looks_like_markdown_report(content)

    @staticmethod
    def _normalize_markdown_headings(content: str) -> str:
        return normalize_markdown_headings(content)

    @staticmethod
    def _normalize_section_bullets(content: str) -> str:
        return normalize_section_bullets(content)

    @staticmethod
    def _repair_markdown_report(content: str, fallback_markdown: str) -> str:
        return repair_markdown_report(content, fallback_markdown)
