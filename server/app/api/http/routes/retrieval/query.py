"""retrieval 검색 라우트."""

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.dependencies import get_retrieval_query_service
from server.app.api.http.routes.retrieval.support import (
    resolve_workspace_id,
    to_search_item_response,
)
from server.app.api.http.schemas.retrieval import RetrievalSearchResponse
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

MAX_SEARCH_LIMIT = 20

router = APIRouter()


@router.get("/search", response_model=RetrievalSearchResponse)
def search_retrieval(
    q: str,
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    limit: int = 10,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> RetrievalSearchResponse:
    """workspace/context 필터 기반 hybrid retrieval 검색."""

    retrieval_query_service = get_retrieval_query_service()
    if retrieval_query_service is None:
        raise HTTPException(status_code=503, detail="retrieval 서비스가 아직 준비되지 않았습니다.")

    workspace_id = resolve_workspace_id(auth_context)
    normalized_limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    items = retrieval_query_service.search(
        workspace_id=workspace_id,
        query=q,
        account_id=account_id,
        contact_id=contact_id,
        context_thread_id=context_thread_id,
        limit=normalized_limit,
    )
    return RetrievalSearchResponse(
        query=q,
        limit=normalized_limit,
        result_count=len(items),
        items=[to_search_item_response(item) for item in items],
    )
