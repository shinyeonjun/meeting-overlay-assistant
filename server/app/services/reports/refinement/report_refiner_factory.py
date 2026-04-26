"""회의록 정제기 생성 팩토리."""

from __future__ import annotations

from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.reports.refinement.llm_markdown_report_refiner import (
    LLMMarkdownReportRefiner,
)
from server.app.services.reports.refinement.noop_report_refiner import NoOpReportRefiner
from server.app.services.reports.refinement.report_refiner import ReportRefiner
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


def create_report_refiner(
    backend_name: str,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
) -> ReportRefiner:
    """설정값에 맞는 회의록 정제기를 생성한다."""

    if backend_name == "noop":
        return NoOpReportRefiner()
    if backend_name == "structured":
        return StructuredMarkdownReportRefiner()

    completion_client = create_llm_completion_client(
        backend_name=backend_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    return LLMMarkdownReportRefiner(completion_client)
