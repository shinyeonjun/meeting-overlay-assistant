"""이벤트와 history 관련 builder."""

from __future__ import annotations

from server.app.services.events.event_lifecycle_service import EventLifecycleService
from server.app.services.events.event_management_service import EventManagementService
from server.app.services.history import CarryOverService, HistoryQueryService


def build_event_management_service(*, meeting_event_repository) -> EventManagementService:
    """이벤트 관리 서비스를 조립한다."""

    return EventManagementService(meeting_event_repository)


def build_event_lifecycle_service(*, meeting_event_repository) -> EventLifecycleService:
    """이벤트 생명주기 서비스를 조립한다."""

    return EventLifecycleService(meeting_event_repository)


def build_history_query_service(
    *,
    session_service,
    report_service,
    context_resolution_service,
    event_management_service,
    retrieval_query_service=None,
) -> HistoryQueryService:
    """history 타임라인 조회 서비스를 조립한다."""

    return HistoryQueryService(
        session_service=session_service,
        report_service=report_service,
        context_resolution_service=context_resolution_service,
        carry_over_service=CarryOverService(event_management_service),
        retrieval_query_service=retrieval_query_service,
    )

