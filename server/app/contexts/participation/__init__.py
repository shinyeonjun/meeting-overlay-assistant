"""참여(Participation) 바운디드 컨텍스트의 공개 API.

회의 참석자, 참여자 해석(연락처 연결), 후속 작업을 다룬다.
다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.

application(서비스)은 지연 로드한다. 회의 도메인(MeetingSession)이 이 패키지의 값 객체를 import하는데,
서비스가 다시 MeetingSession을 import하므로 즉시 로드하면 순환 import가 생긴다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from server.app.contexts.participation.domain import (
    ParticipantFollowup,
    SessionParticipant,
    SessionParticipantCandidate,
    SessionParticipantCandidateMatch,
    SessionParticipationSummary,
    SessionParticipationView,
    normalize_participant_name,
    normalize_participant_names,
    normalize_session_participants,
)

if TYPE_CHECKING:  # pragma: no cover
    from server.app.contexts.participation.application import (
        ParticipantFollowupService,
        ParticipantResolutionService,
        ParticipationQueryService,
    )

_LAZY_APPLICATION_NAMES = {
    "ParticipantFollowupService",
    "ParticipantResolutionService",
    "ParticipationQueryService",
}

__all__ = [
    "ParticipantFollowup",
    "ParticipantFollowupService",
    "ParticipantResolutionService",
    "ParticipationQueryService",
    "SessionParticipant",
    "SessionParticipantCandidate",
    "SessionParticipantCandidateMatch",
    "SessionParticipationSummary",
    "SessionParticipationView",
    "normalize_participant_name",
    "normalize_participant_names",
    "normalize_session_participants",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_APPLICATION_NAMES:
        module = import_module("server.app.contexts.participation.application")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
