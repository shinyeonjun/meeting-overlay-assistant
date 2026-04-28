"""회의록/요약 계열 shared singleton 생성기."""

from __future__ import annotations

from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.reports.minutes import (
    LLMMeetingMinutesAnalyzer,
    MeetingMinutesAnalyzerConfig,
    NoOpMeetingMinutesAnalyzer,
)
from server.app.services.sessions.workspace_summary_synthesizer import (
    LLMWorkspaceSummarySynthesizer,
    NoOpWorkspaceSummarySynthesizer,
)
from server.app.services.sessions.topic_summarizer import (
    LLMTopicSummarizer,
    NoOpTopicSummarizer,
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


def create_shared_workspace_summary_synthesizer(
    *,
    settings,
    resolve_workspace_summary_synthesizer_service_profile,
):
    """공용 workspace summary synthesizer를 만든다."""

    profile = resolve_workspace_summary_synthesizer_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpWorkspaceSummarySynthesizer()

    completion_client = create_llm_completion_client(
        backend_name=profile.completion_client.backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return LLMWorkspaceSummarySynthesizer(
        completion_client,
        model=profile.completion_client.model,
    )


def create_shared_meeting_minutes_analyzer(*, settings):
    """공용 회의록 AI 분석기를 만든다."""

    backend_name = settings.meeting_minutes_analyzer_backend.strip().lower()
    if backend_name == "noop":
        return NoOpMeetingMinutesAnalyzer()

    completion_client = create_llm_completion_client(
        backend_name=backend_name,
        model=settings.meeting_minutes_analyzer_model,
        base_url=(
            settings.meeting_minutes_analyzer_base_url
            or "http://127.0.0.1:11434/v1"
        ),
        api_key=settings.meeting_minutes_analyzer_api_key,
        timeout_seconds=settings.meeting_minutes_analyzer_timeout_seconds,
    )
    return LLMMeetingMinutesAnalyzer(
        completion_client,
        config=MeetingMinutesAnalyzerConfig(
            model=settings.meeting_minutes_analyzer_model,
            max_transcript_chars=settings.meeting_minutes_analyzer_max_transcript_chars,
            map_reduce_segment_threshold=(
                settings.meeting_minutes_analyzer_map_reduce_segment_threshold
            ),
            max_segments_per_chunk=settings.meeting_minutes_analyzer_max_segments_per_chunk,
            use_response_schema=backend_name != "ollama",
        ),
    )
