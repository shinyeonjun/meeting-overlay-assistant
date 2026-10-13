"""meeting 바운디드 컨텍스트의 공개 API.

다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any


_LAZY_NAMES = {
    "LLMTopicSummarizer": "server.app.contexts.meeting.application.sessions.topic_helpers.llm",
    "NoOpTopicSummarizer": "server.app.contexts.meeting.application.sessions.topic_helpers.heuristic",
    "SessionFinalizationService": "server.app.contexts.meeting.application.sessions.session_finalization_service",
    "SessionOverviewBuilder": "server.app.contexts.meeting.application.sessions.overview_builder",
    "SessionOverviewService": "server.app.contexts.meeting.application.sessions.session_overview_service",
    "SessionRecoveryService": "server.app.contexts.meeting.application.sessions.session_recovery_service",
    "SessionService": "server.app.contexts.meeting.application.sessions.session_service",
    "run_session_runtime_heartbeat": "server.app.contexts.meeting.application.sessions.session_runtime_heartbeat",
    "SpeakerNameService": "server.app.contexts.meeting.application.sessions.speaker_name_service",
    "SpeakerNamesLockedError": "server.app.contexts.meeting.application.sessions.speaker_name_service",
    "SpeakerNotFoundError": "server.app.contexts.meeting.application.sessions.speaker_name_service",
}

__all__ = [
    "LLMTopicSummarizer",
    "NoOpTopicSummarizer",
    "SessionFinalizationService",
    "SessionOverviewBuilder",
    "SessionOverviewService",
    "SessionRecoveryService",
    "SessionService",
    "SpeakerNameService",
    "SpeakerNamesLockedError",
    "SpeakerNotFoundError",
    "run_session_runtime_heartbeat",
]


_LAZY_MODULES: dict[str, str] = {}


def __getattr__(name: str) -> Any:
    if name in _LAZY_MODULES:
        return import_module(_LAZY_MODULES[name])
    if name in _LAZY_NAMES:
        return getattr(import_module(_LAZY_NAMES[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
