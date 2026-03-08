from __future__ import annotations

from backend.app.services.reports.refinement.llm_markdown_report_refiner import (
    LLMMarkdownReportRefiner,
)
from backend.app.services.reports.refinement.noop_report_refiner import NoOpReportRefiner
from backend.app.services.reports.refinement.report_refiner_factory import (
    create_report_refiner,
)
from backend.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class TestReportRefinerFactory:
    def test_noop_backend면_noop_refiner를_반환한다(self):
        refiner = create_report_refiner(
            backend_name="noop",
            model="ignored",
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            timeout_seconds=10,
        )

        assert isinstance(refiner, NoOpReportRefiner)

    def test_structured_backend면_structured_refiner를_반환한다(self):
        refiner = create_report_refiner(
            backend_name="structured",
            model="ignored",
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            timeout_seconds=10,
        )

        assert isinstance(refiner, StructuredMarkdownReportRefiner)

    def test_llm_backend면_llm_refiner를_반환한다(self):
        refiner = create_report_refiner(
            backend_name="ollama",
            model="qwen2.5:3b-instruct",
            base_url="http://127.0.0.1:11434/v1",
            api_key=None,
            timeout_seconds=10,
        )

        assert isinstance(refiner, LLMMarkdownReportRefiner)
