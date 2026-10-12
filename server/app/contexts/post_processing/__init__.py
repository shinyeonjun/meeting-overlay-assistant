"""post_processing 바운디드 컨텍스트의 공개 API.

다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any


_LAZY_NAMES = {
    "PostMeetingPipelineRecoveryService": "server.app.contexts.post_processing.application.post_meeting_pipeline_recovery_service",
    "PostMeetingPipelineService": "server.app.contexts.post_processing.application.post_meeting_pipeline_service",
    "SessionPostProcessingJobService": "server.app.contexts.post_processing.application.session_post_processing_job_service",
    "SpeakerDiarizer": "server.app.contexts.post_processing.application.diarization.speaker_diarizer",
    "SpeakerSegment": "server.app.contexts.post_processing.application.diarization.speaker_diarizer",
    "create_speaker_diarizer": "server.app.contexts.post_processing.application.diarization.speaker_diarizer_factory",
}

__all__ = [
    "PostMeetingPipelineRecoveryService",
    "PostMeetingPipelineService",
    "SessionPostProcessingJobService",
    "SpeakerDiarizer",
    "SpeakerSegment",
    "create_speaker_diarizer",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_NAMES:
        return getattr(import_module(_LAZY_NAMES[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
