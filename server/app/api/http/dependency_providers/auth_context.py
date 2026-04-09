"""인증/세션/맥락 관련 dependency provider."""

from __future__ import annotations

from server.app.api.http.wiring import service_builders
from server.app.api.http.wiring.persistence import (
    get_auth_repository,
    get_meeting_context_repository,
    get_participant_followup_repository,
    get_session_repository,
)
from server.app.core.config import settings


def get_auth_service():
    """인증 서비스를 조립한다."""

    return service_builders.build_auth_service(
        auth_repository=get_auth_repository(),
        session_ttl_hours=settings.auth_session_ttl_hours,
    )


def get_session_recovery_service():
    """세션 복구 서비스를 조립한다."""

    from server.app.api.http.dependencies import get_live_stream_service

    return service_builders.build_session_recovery_service(
        session_repository=get_session_repository(),
        live_stream_service=get_live_stream_service(),
    )


def get_session_service():
    """세션 서비스를 조립한다."""

    return service_builders.build_session_service(
        session_repository=get_session_repository(),
        meeting_context_repository=get_meeting_context_repository(),
        recovery_service=get_session_recovery_service(),
    )


def get_meeting_context_service():
    """회의 맥락 서비스를 조립한다."""

    return service_builders.build_meeting_context_service(
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_context_catalog_service():
    """맥락 catalog 서비스를 조립한다."""

    return service_builders.build_context_catalog_service(
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_context_resolution_service():
    """맥락 해석 서비스를 조립한다."""

    return service_builders.build_context_resolution_service(
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_participant_followup_service():
    """참여자 후속 작업 서비스를 조립한다."""

    return service_builders.build_participant_followup_service(
        participant_followup_repository=get_participant_followup_repository(),
        meeting_context_repository=get_meeting_context_repository(),
    )


def get_participation_query_service():
    """참여자 상세 조회 서비스를 조립한다."""

    return service_builders.build_participation_query_service(
        participant_followup_repository=get_participant_followup_repository(),
        meeting_context_repository=get_meeting_context_repository(),
    )
