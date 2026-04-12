"""인증, 세션, 맥락, 참여자 관련 서비스 builder."""

from __future__ import annotations

from server.app.services.auth.auth_service import AuthService
from server.app.services.context.context_catalog_service import ContextCatalogService
from server.app.services.context.context_resolution_service import ContextResolutionService
from server.app.services.context.meeting_context_service import MeetingContextService
from server.app.services.participation.participant_followup_service import (
    ParticipantFollowupService,
)
from server.app.services.participation.participation_query_service import (
    ParticipationQueryService,
)
from server.app.services.participation.participant_resolution_service import (
    ParticipantResolutionService,
)
from server.app.services.sessions.session_recovery_service import SessionRecoveryService
from server.app.services.sessions.session_service import SessionService


def build_auth_service(*, auth_repository, session_ttl_hours: int) -> AuthService:
    """인증 서비스를 조립한다."""

    return AuthService(
        repository=auth_repository,
        session_ttl_hours=session_ttl_hours,
    )


def build_session_recovery_service(
    *,
    session_repository,
    live_stream_service,
) -> SessionRecoveryService:
    """세션 복구 서비스를 조립한다."""

    return SessionRecoveryService(
        session_repository=session_repository,
        live_stream_service=live_stream_service,
    )


def build_session_service(
    *,
    session_repository,
    meeting_context_repository,
    recovery_service=None,
) -> SessionService:
    """세션 서비스를 조립한다."""

    return SessionService(
        session_repository,
        meeting_context_repository,
        recovery_service=recovery_service,
    )


def build_meeting_context_service(*, meeting_context_repository) -> MeetingContextService:
    """회의 맥락 서비스를 조립한다."""

    return MeetingContextService(meeting_context_repository)


def build_context_catalog_service(*, meeting_context_repository) -> ContextCatalogService:
    """맥락 catalog 서비스를 조립한다."""

    return ContextCatalogService(meeting_context_repository)


def build_context_resolution_service(*, meeting_context_repository) -> ContextResolutionService:
    """맥락 해석 서비스를 조립한다."""

    return ContextResolutionService(
        build_context_catalog_service(meeting_context_repository=meeting_context_repository)
    )


def build_participant_followup_service(
    *,
    participant_followup_repository,
    meeting_context_repository,
) -> ParticipantFollowupService:
    """참여자 후속 작업 서비스를 조립한다."""

    return ParticipantFollowupService(
        participant_followup_repository=participant_followup_repository,
        participant_resolution_service=ParticipantResolutionService(
            meeting_context_repository=meeting_context_repository,
        ),
    )


def build_participation_query_service(
    *,
    meeting_context_repository,
    participant_followup_repository,
) -> ParticipationQueryService:
    """참여자 상세 조회 서비스를 조립한다."""

    participant_resolution_service = ParticipantResolutionService(
        meeting_context_repository=meeting_context_repository,
    )
    participant_followup_service = ParticipantFollowupService(
        participant_followup_repository=participant_followup_repository,
        participant_resolution_service=participant_resolution_service,
    )
    return ParticipationQueryService(
        participant_resolution_service=participant_resolution_service,
        participant_followup_service=participant_followup_service,
    )
