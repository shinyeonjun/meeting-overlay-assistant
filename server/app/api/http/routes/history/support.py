"""HTTP 계층에서 히스토리 관련 support 구성을 담당한다."""
from server.app.api.http.schemas.history import (
    HistoryCarryOverItemResponse,
    HistoryCarryOverResponse,
    HistoryRetrievalBriefItemResponse,
    HistoryRetrievalBriefResponse,
    HistoryTimelineReportItemResponse,
    HistoryTimelineSessionItemResponse,
)
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.services.history import HistoryCarryOver, HistoryRetrievalBrief


def resolve_workspace_id(auth_context: AuthenticatedSession | None) -> str:
    """요청에 사용할 workspace id를 결정한다."""

    if auth_context is None:
        return DEFAULT_WORKSPACE_ID
    return auth_context.user.workspace_id or DEFAULT_WORKSPACE_ID


def to_timeline_session_item(item) -> HistoryTimelineSessionItemResponse:
    """세션을 history 타임라인 항목으로 변환한다."""

    return HistoryTimelineSessionItemResponse(
        id=item.id,
        title=item.title,
        status=item.status.value,
        primary_input_source=item.primary_input_source,
        started_at=item.started_at,
        ended_at=item.ended_at,
        recording_artifact_id=item.recording_artifact_id,
        post_processing_status=item.post_processing_status,
        post_processing_error_message=item.post_processing_error_message,
        post_processing_requested_at=item.post_processing_requested_at,
        post_processing_started_at=item.post_processing_started_at,
        post_processing_completed_at=item.post_processing_completed_at,
        canonical_transcript_version=item.canonical_transcript_version,
        canonical_events_version=item.canonical_events_version,
        account_id=item.account_id,
        contact_id=item.contact_id,
        context_thread_id=item.context_thread_id,
    )


def to_timeline_report_item(item) -> HistoryTimelineReportItemResponse:
    """리포트를 history 타임라인 항목으로 변환한다."""

    return HistoryTimelineReportItemResponse(
        id=item.id,
        session_id=item.session_id,
        report_type=item.report_type,
        version=item.version,
        generated_at=item.generated_at,
        file_artifact_id=item.file_artifact_id,
        file_path=item.file_path,
        insight_source=item.insight_source,
    )


def to_carry_over_response(carry_over: HistoryCarryOver, sessions_by_id: dict[str, object]) -> HistoryCarryOverResponse:
    """carry-over 계산 결과를 API 응답으로 변환한다."""

    return HistoryCarryOverResponse(
        decisions=[to_carry_over_item(event, sessions_by_id=sessions_by_id) for event in carry_over.decisions],
        action_items=[to_carry_over_item(event, sessions_by_id=sessions_by_id) for event in carry_over.action_items],
        risks=[to_carry_over_item(event, sessions_by_id=sessions_by_id) for event in carry_over.risks],
        questions=[to_carry_over_item(event, sessions_by_id=sessions_by_id) for event in carry_over.questions],
    )


def to_carry_over_item(event, *, sessions_by_id: dict[str, object]) -> HistoryCarryOverItemResponse:
    """이벤트를 carry-over 항목으로 변환한다."""

    session = sessions_by_id.get(event.session_id)
    return HistoryCarryOverItemResponse(
        event_id=event.id,
        session_id=event.session_id,
        session_title=session.title if session is not None else "",
        event_type=event.event_type.value,
        title=event.title,
        state=event.state.value,
        updated_at_ms=event.updated_at_ms,
    )


def to_retrieval_brief_response(brief: HistoryRetrievalBrief) -> HistoryRetrievalBriefResponse:
    """retrieval brief를 history 응답 모델로 변환한다."""

    return HistoryRetrievalBriefResponse(
        query=brief.query,
        result_count=len(brief.items),
        items=[
            HistoryRetrievalBriefItemResponse(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                source_type=item.source_type,
                source_id=item.source_id,
                document_title=item.document_title,
                chunk_text=item.chunk_text,
                chunk_heading=item.chunk_heading,
                distance=item.distance,
                session_id=item.session_id,
                report_id=item.report_id,
                account_id=item.account_id,
                contact_id=item.contact_id,
                context_thread_id=item.context_thread_id,
            )
            for item in brief.items
        ],
    )
