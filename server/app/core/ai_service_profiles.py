"""LLM/분석 서비스 프로파일 resolver."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from server.app.core.config import AppConfig


@dataclass(frozen=True)
class CompletionClientProfile:
    """Completion client 최종 설정."""

    backend_name: str
    model: str
    base_url: str
    api_key: str | None
    timeout_seconds: float


@dataclass(frozen=True)
class AnalyzerServiceProfile:
    """분석기 최종 설정."""

    backend_name: str
    completion_client: CompletionClientProfile
    analyzer_stages: tuple[str, ...] = ()


@dataclass(frozen=True)
class TopicSummarizerServiceProfile:
    """주제 요약기 최종 설정."""

    backend_name: str
    completion_client: CompletionClientProfile


@dataclass(frozen=True)
class WorkspaceSummarySynthesizerServiceProfile:
    """워크스페이스 요약 합성기 최종 설정."""

    backend_name: str
    completion_client: CompletionClientProfile


@dataclass(frozen=True)
class LiveEventCorrectorServiceProfile:
    """실시간 이벤트 보정기 최종 설정."""

    backend_name: str
    completion_client: CompletionClientProfile
    target_event_types: tuple[str, ...]
    min_utterance_confidence: float
    min_text_length: int
    max_workers: int


@lru_cache(maxsize=1)
def _load_ai_service_profiles(config_path: str) -> dict[str, Any]:
    return json.loads(Path(config_path).read_text(encoding="utf-8-sig"))


def resolve_completion_client_profile(
    profile_name: str,
    settings: AppConfig,
    *,
    fallback_model: str,
    fallback_base_url: str,
    fallback_api_key: str | None,
    fallback_timeout_seconds: float,
) -> CompletionClientProfile:
    """completion client 프로파일을 로드하고 fallback을 반영한다."""
    profiles = _load_ai_service_profiles(str(settings.ai_service_profiles_config_path))
    profile = profiles.get("completion_clients", {}).get(profile_name, {})

    backend_name = str(profile.get("backend_name", profile_name))
    if backend_name == "noop":
        return CompletionClientProfile(
            backend_name="noop",
            model="ignored",
            base_url=fallback_base_url,
            api_key=fallback_api_key,
            timeout_seconds=fallback_timeout_seconds,
        )

    return CompletionClientProfile(
        backend_name=backend_name,
        model=str(profile.get("model", fallback_model)),
        base_url=str(profile.get("base_url", fallback_base_url)),
        api_key=str(profile["api_key"]) if profile.get("api_key") else fallback_api_key,
        timeout_seconds=float(profile.get("timeout_seconds", fallback_timeout_seconds)),
    )


def resolve_analyzer_service_profile_for_backend(
    settings: AppConfig,
    backend_name: str,
) -> AnalyzerServiceProfile:
    """분석기 프로파일을 로드한다."""
    profiles = _load_ai_service_profiles(str(settings.ai_service_profiles_config_path))
    profile = profiles.get("analyzers", {}).get(backend_name, {})
    completion_profile_name = str(
        profile.get("completion_profile", settings.llm_provider_backend)
    )
    completion_client = resolve_completion_client_profile(
        completion_profile_name,
        settings,
        fallback_model=settings.llm_model,
        fallback_base_url=settings.llm_base_url,
        fallback_api_key=settings.llm_api_key,
        fallback_timeout_seconds=settings.llm_timeout_seconds,
    )
    return AnalyzerServiceProfile(
        backend_name=str(profile.get("backend_name", backend_name)),
        completion_client=completion_client,
        analyzer_stages=tuple(str(stage) for stage in profile.get("analyzer_stages", [])),
    )


def resolve_analyzer_service_profile(settings: AppConfig) -> AnalyzerServiceProfile:
    """기존 전역 analyzer 프로필을 해석한다."""

    return resolve_analyzer_service_profile_for_backend(settings, settings.analyzer_backend)


def resolve_live_analyzer_service_profile(settings: AppConfig) -> AnalyzerServiceProfile:
    """실시간 입력 경로의 analyzer 프로필을 해석한다."""

    return resolve_analyzer_service_profile_for_backend(
        settings,
        settings.live_analyzer_backend,
    )


def resolve_post_processing_analyzer_service_profile(
    settings: AppConfig,
) -> AnalyzerServiceProfile:
    """회의 후처리 경로의 analyzer 프로필을 해석한다."""

    return resolve_analyzer_service_profile_for_backend(
        settings,
        settings.post_processing_analyzer_backend,
    )


def resolve_report_analyzer_service_profile(settings: AppConfig) -> AnalyzerServiceProfile:
    """회의록 fallback 경로의 analyzer 프로필을 해석한다."""

    return resolve_analyzer_service_profile_for_backend(
        settings,
        settings.report_analyzer_backend,
    )


def resolve_topic_summarizer_service_profile(
    settings: AppConfig,
) -> TopicSummarizerServiceProfile:
    """주제 요약기 프로파일을 로드한다."""
    profiles = _load_ai_service_profiles(str(settings.ai_service_profiles_config_path))
    profile = profiles.get("topic_summarizers", {}).get(settings.topic_summarizer_backend, {})
    completion_profile_name = str(
        profile.get("completion_profile", settings.topic_summarizer_backend)
    )
    completion_client = resolve_completion_client_profile(
        completion_profile_name,
        settings,
        fallback_model=settings.topic_summarizer_model,
        fallback_base_url=settings.topic_summarizer_base_url,
        fallback_api_key=settings.topic_summarizer_api_key,
        fallback_timeout_seconds=settings.topic_summarizer_timeout_seconds,
    )
    return TopicSummarizerServiceProfile(
        backend_name=str(profile.get("backend_name", settings.topic_summarizer_backend)),
        completion_client=completion_client,
    )


def resolve_workspace_summary_synthesizer_service_profile(
    settings: AppConfig,
) -> WorkspaceSummarySynthesizerServiceProfile:
    """워크스페이스 요약 합성기 프로파일을 로드한다."""
    profiles = _load_ai_service_profiles(str(settings.ai_service_profiles_config_path))
    profile = profiles.get("workspace_summary_synthesizers", {}).get(
        settings.workspace_summary_synthesizer_backend,
        {},
    )
    completion_profile_name = str(
        profile.get(
            "completion_profile",
            settings.workspace_summary_synthesizer_backend,
        )
    )
    completion_client = resolve_completion_client_profile(
        completion_profile_name,
        settings,
        fallback_model=settings.workspace_summary_synthesizer_model,
        fallback_base_url=settings.workspace_summary_synthesizer_base_url,
        fallback_api_key=settings.workspace_summary_synthesizer_api_key,
        fallback_timeout_seconds=settings.workspace_summary_synthesizer_timeout_seconds,
    )
    return WorkspaceSummarySynthesizerServiceProfile(
        backend_name=str(
            profile.get(
                "backend_name",
                settings.workspace_summary_synthesizer_backend,
            )
        ),
        completion_client=completion_client,
    )


def resolve_live_event_corrector_service_profile(
    settings: AppConfig,
) -> LiveEventCorrectorServiceProfile:
    """실시간 이벤트 보정기 프로파일을 로드한다."""
    profiles = _load_ai_service_profiles(str(settings.ai_service_profiles_config_path))
    profile = profiles.get("live_event_correctors", {}).get("default", {})
    backend_name = str(profile.get("backend_name", "noop"))
    if backend_name == "noop":
        return LiveEventCorrectorServiceProfile(
            backend_name="noop",
            completion_client=resolve_completion_client_profile(
                "noop",
                settings,
                fallback_model=settings.llm_model,
                fallback_base_url=settings.llm_base_url,
                fallback_api_key=settings.llm_api_key,
                fallback_timeout_seconds=settings.llm_timeout_seconds,
            ),
            target_event_types=(),
            min_utterance_confidence=0.0,
            min_text_length=0,
            max_workers=1,
        )

    completion_profile_name = str(profile.get("completion_profile", "analysis_default"))
    completion_client = resolve_completion_client_profile(
        completion_profile_name,
        settings,
        fallback_model=settings.llm_model,
        fallback_base_url=settings.llm_base_url,
        fallback_api_key=settings.llm_api_key,
        fallback_timeout_seconds=settings.llm_timeout_seconds,
    )
    return LiveEventCorrectorServiceProfile(
        backend_name=backend_name,
        completion_client=completion_client,
        target_event_types=tuple(profile.get("target_event_types", [])),
        min_utterance_confidence=float(profile.get("min_utterance_confidence", 0.0)),
        min_text_length=int(profile.get("min_text_length", 0)),
        max_workers=int(profile.get("max_workers", 1)),
    )
