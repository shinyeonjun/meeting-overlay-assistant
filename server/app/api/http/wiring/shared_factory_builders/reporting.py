"""HTTP 계층에서 공통 관련 reporting 구성을 담당한다."""
from __future__ import annotations

from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.reports.refinement.report_refiner_factory import (
    create_report_refiner,
)
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)
from server.app.services.sessions.topic_summarizer import (
    LLMTopicSummarizer,
    NoOpTopicSummarizer,
)


def create_shared_report_refiner(*, settings, resolve_report_refiner_service_profile):
    """공용 report refiner를 만든다."""

    profile = resolve_report_refiner_service_profile(settings)
    if profile.backend_name == "noop":
        return StructuredMarkdownReportRefiner()

    backend_name = profile.backend_name
    if backend_name == "llm":
        backend_name = profile.completion_client.backend_name

    return create_report_refiner(
        backend_name=backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )


def create_shared_topic_summarizer(*, settings, resolve_topic_summarizer_service_profile):
    """공용 topic summarizer를 만든다."""

    profile = resolve_topic_summarizer_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpTopicSummarizer()

    completion_client = create_llm_completion_client(
        backend_name=profile.completion_client.backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return LLMTopicSummarizer(completion_client)
