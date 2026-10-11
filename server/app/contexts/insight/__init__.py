"""insight 바운디드 컨텍스트의 공개 API.

다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from server.app.contexts.insight.domain.meeting_event import (
    MeetingEvent,
)

_LAZY_NAMES = {
    "AsyncLiveEventCorrectionService": "server.app.contexts.insight.application.analysis.correction.live_event_correction_service",
    "EventLifecycleService": "server.app.contexts.insight.application.events.event_lifecycle_service",
    "EventManagementService": "server.app.contexts.insight.application.events.event_management_service",
    "FallbackMeetingAnalyzer": "server.app.contexts.insight.application.analysis.analyzers.fallback_meeting_analyzer",
    "InsightPipelineMeetingAnalyzer": "server.app.contexts.insight.application.analysis.analyzers.insight_pipeline_meeting_analyzer",
    "LIVE_QUESTION_RESPONSE_SCHEMA": "server.app.contexts.insight.application.live_questions.question_prompt_builder",
    "LLMAnalysisInput": "server.app.contexts.insight.application.analysis.llm.contracts.llm_models",
    "LLMAnalysisPromptBuilder": "server.app.contexts.insight.application.analysis.llm.extraction.llm_prompt_builder",
    "LLMAnalysisProvider": "server.app.contexts.insight.application.analysis.llm.contracts.llm_provider",
    "LLMAnalysisResponseParser": "server.app.contexts.insight.application.analysis.llm.extraction.llm_response_parser",
    "LLMAnalysisResult": "server.app.contexts.insight.application.analysis.llm.contracts.llm_models",
    "LLMBasedMeetingAnalyzer": "server.app.contexts.insight.application.analysis.analyzers.llm_based_meeting_analyzer",
    "LLMCompletionClient": "server.app.contexts.insight.application.analysis.llm.contracts.llm_completion_client",
    "LLMEventCandidate": "server.app.contexts.insight.application.analysis.llm.contracts.llm_models",
    "LiveQuestionAnalysisWorkerService": "server.app.contexts.insight.application.live_questions.question_analysis_worker_service",
    "LiveQuestionDispatchService": "server.app.contexts.insight.application.live_questions.question_dispatch_service",
    "LiveQuestionItem": "server.app.contexts.insight.application.live_questions.models",
    "LiveQuestionLLMClient": "server.app.contexts.insight.application.live_questions.question_llm_client",
    "LiveQuestionOperation": "server.app.contexts.insight.application.live_questions.models",
    "LiveQuestionRequest": "server.app.contexts.insight.application.live_questions.models",
    "LiveQuestionResult": "server.app.contexts.insight.application.live_questions.models",
    "LiveQuestionResultConsumer": "server.app.contexts.insight.application.live_questions.question_result_consumer",
    "LiveQuestionStateStore": "server.app.contexts.insight.application.live_questions.question_state_store",
    "LiveQuestionUtterance": "server.app.contexts.insight.application.live_questions.models",
    "MeetingAnalyzer": "server.app.contexts.insight.application.analysis.analyzers.analyzer",
    "MeetingEventService": "server.app.contexts.insight.application.events.meeting_event_service",
    "NoOpLLMAnalysisProvider": "server.app.contexts.insight.application.analysis.llm.providers.noop_llm_analysis_provider",
    "NoOpLLMCompletionClient": "server.app.contexts.insight.application.analysis.llm.clients.noop_llm_completion_client",
    "NoOpLiveEventCorrectionService": "server.app.contexts.insight.application.analysis.correction.live_event_correction_service",
    "NoOpLiveQuestionDispatchService": "server.app.contexts.insight.application.live_questions.question_dispatch_service",
    "OllamaCompletionClient": "server.app.contexts.insight.application.analysis.llm.clients.ollama_completion_client",
    "OpenAICompatibleCompletionClient": "server.app.contexts.insight.application.analysis.llm.clients.openai_compatible_completion_client",
    "PromptBasedLLMAnalysisProvider": "server.app.contexts.insight.application.analysis.llm.providers.prompt_based_llm_analysis_provider",
    "QuestionTextNormalizer": "server.app.contexts.insight.application.live_questions.question_text_normalizer",
    "RuleBasedMeetingAnalyzer": "server.app.contexts.insight.application.analysis.analyzers.rule_based_meeting_analyzer",
    "build_question_analysis_system_prompt": "server.app.contexts.insight.application.live_questions.question_prompt_builder",
    "build_question_analysis_warmup_prompt": "server.app.contexts.insight.application.live_questions.question_prompt_builder",
    "create_llm_analysis_provider": "server.app.contexts.insight.application.analysis.llm.factories.llm_provider_factory",
    "create_llm_completion_client": "server.app.contexts.insight.application.analysis.llm.factories.completion_client_factory",
    "create_meeting_analyzer": "server.app.contexts.insight.application.analysis.analyzers.analyzer_factory",
    "filter_insight_event_type_values": "server.app.contexts.insight.application.analysis.event_type_policy",
    "get_insight_metrics_snapshot": "server.app.contexts.insight.application.analysis.observability.insight_metrics",
    "load_question_text_normalizer_from_env": "server.app.contexts.insight.application.live_questions.question_text_normalizer",
}

__all__ = [
    "AsyncLiveEventCorrectionService",
    "EventLifecycleService",
    "EventManagementService",
    "FallbackMeetingAnalyzer",
    "InsightPipelineMeetingAnalyzer",
    "LIVE_QUESTION_RESPONSE_SCHEMA",
    "LLMAnalysisInput",
    "LLMAnalysisPromptBuilder",
    "LLMAnalysisProvider",
    "LLMAnalysisResponseParser",
    "LLMAnalysisResult",
    "LLMBasedMeetingAnalyzer",
    "LLMCompletionClient",
    "LLMEventCandidate",
    "LiveQuestionAnalysisWorkerService",
    "LiveQuestionDispatchService",
    "LiveQuestionItem",
    "LiveQuestionLLMClient",
    "LiveQuestionOperation",
    "LiveQuestionRequest",
    "LiveQuestionResult",
    "LiveQuestionResultConsumer",
    "LiveQuestionStateStore",
    "LiveQuestionUtterance",
    "MeetingAnalyzer",
    "MeetingEvent",
    "MeetingEventService",
    "NoOpLLMAnalysisProvider",
    "NoOpLLMCompletionClient",
    "NoOpLiveEventCorrectionService",
    "NoOpLiveQuestionDispatchService",
    "OllamaCompletionClient",
    "OpenAICompatibleCompletionClient",
    "PromptBasedLLMAnalysisProvider",
    "QuestionTextNormalizer",
    "RuleBasedMeetingAnalyzer",
    "build_question_analysis_system_prompt",
    "build_question_analysis_warmup_prompt",
    "create_llm_analysis_provider",
    "create_llm_completion_client",
    "create_meeting_analyzer",
    "filter_insight_event_type_values",
    "get_insight_metrics_snapshot",
    "load_question_text_normalizer_from_env",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_NAMES:
        return getattr(import_module(_LAZY_NAMES[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
