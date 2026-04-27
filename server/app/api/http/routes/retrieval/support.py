"""retrieval 라우트 공통 보조 함수."""

from server.app.api.http.schemas.retrieval import RetrievalSearchItemResponse
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.models.auth_session import AuthenticatedSession


def resolve_workspace_id(auth_context: AuthenticatedSession | None) -> str:
    """요청 사용자의 workspace id를 결정한다."""

    if auth_context is None:
        return DEFAULT_WORKSPACE_ID
    return auth_context.user.workspace_id or DEFAULT_WORKSPACE_ID


def to_search_item_response(item) -> RetrievalSearchItemResponse:
    """retrieval 검색 결과를 API 응답으로 변환한다."""

    return RetrievalSearchItemResponse(
        chunk_id=item.chunk_id,
        document_id=item.document_id,
        source_type=item.source_type,
        source_id=item.source_id,
        document_title=item.document_title,
        chunk_text=item.chunk_text,
        chunk_heading=item.chunk_heading,
        distance=item.distance,
        source_ref=item.source_ref,
        speaker_label=item.speaker_label,
        start_ms=item.start_ms,
        end_ms=item.end_ms,
        metadata_json=item.metadata_json,
        session_id=item.session_id,
        report_id=item.report_id,
        account_id=item.account_id,
        contact_id=item.contact_id,
        context_thread_id=item.context_thread_id,
    )
