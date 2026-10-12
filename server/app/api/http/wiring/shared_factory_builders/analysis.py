"""분석 계열 shared singleton 생성기."""

from __future__ import annotations

from server.app.contexts.insight import create_meeting_analyzer
from server.app.contexts.insight import (
    AsyncLiveEventCorrectionService,
    NoOpLiveEventCorrectionService,
)
from server.app.contexts.insight import filter_insight_event_type_values
from server.app.contexts.insight import MeetingEventService


def create_shared_analyzer(*, settings, resolve_analyzer_service_profile):
    """공용 analyzer 인스턴스를 만든다."""

    profile = resolve_analyzer_service_profile(settings)
    return create_meeting_analyzer(
        backend_name=profile.backend_name,
        rules_config_path=str(settings.analysis_rules_config_path),
        llm_provider_backend=profile.completion_client.backend_name,
        llm_model=profile.completion_client.model,
        llm_base_url=profile.completion_client.base_url,
        llm_api_key=profile.completion_client.api_key,
        llm_timeout_seconds=profile.completion_client.timeout_seconds,
        analyzer_chain=profile.analyzer_stages,
    )


def create_live_inline_analyzer(*, settings):
    """라이브 확정 경로에서 동기로 돌릴 analyzer를 만든다.

    확정 자막마다 바로 호출되므로 LLM을 부르지 않는 규칙 기반 분석기만 쓴다.
    LLM 품질의 실시간 질문 분석은 비동기 live question worker가 맡는다.
    LLM을 여기서 부르면 응답(최대 타임아웃)을 기다리는 동안 확정 처리 전체가 멈춘다.
    """

    return create_meeting_analyzer(
        backend_name="rule_based",
        rules_config_path=str(settings.analysis_rules_config_path),
    )


def create_shared_live_event_corrector(
    *,
    settings,
    resolve_live_event_corrector_service_profile,
    event_repository,
    transaction_manager,
    EventType,
):
    """공용 live event corrector를 만든다."""

    profile = resolve_live_event_corrector_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpLiveEventCorrectionService()

    target_event_types = tuple(
        EventType(event_type) for event_type in filter_insight_event_type_values(profile.target_event_types)
    )
    analyzer = create_meeting_analyzer(
        backend_name="llm",
        rules_config_path=str(settings.analysis_rules_config_path),
        llm_provider_backend=profile.completion_client.backend_name,
        llm_model=profile.completion_client.model,
        llm_base_url=profile.completion_client.base_url,
        llm_api_key=profile.completion_client.api_key,
        llm_timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return AsyncLiveEventCorrectionService(
        analyzer=analyzer,
        event_service=MeetingEventService(event_repository),
        transaction_manager=transaction_manager,
        target_event_types=target_event_types,
        min_utterance_confidence=profile.min_utterance_confidence,
        min_text_length=profile.min_text_length,
        max_workers=profile.max_workers,
    )
