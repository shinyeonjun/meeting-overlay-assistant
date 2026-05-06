"""assistant RAG 검색 실행기."""

from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.models import AssistantQueryPlan
from server.app.services.assistant.chat.retrieval.context_ranker import (
    select_context_sources,
)
from server.app.services.retrieval import RetrievalQueryService

DEFAULT_SEARCH_LIMIT = 12
DEFAULT_CONTEXT_LIMIT = 6


class AssistantRagRetriever:
    """pgvector/FTS hybrid retrieval 결과를 답변 context로 정리한다."""

    def __init__(
        self,
        *,
        retrieval_query_service: RetrievalQueryService,
        search_limit: int = DEFAULT_SEARCH_LIMIT,
        context_limit: int = DEFAULT_CONTEXT_LIMIT,
    ) -> None:
        self._retrieval_query_service = retrieval_query_service
        self._search_limit = max(1, search_limit)
        self._context_limit = max(1, min(context_limit, self._search_limit))

    def retrieve(
        self,
        *,
        workspace_id: str,
        plan: AssistantQueryPlan,
        requested_source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int | None = None,
    ) -> list[RetrievalSearchResult]:
        """질문 계획을 사용해 근거 후보를 찾고 답변에 넣을 chunk를 고른다."""

        search_limit = max(1, min(limit or self._search_limit, self._search_limit))
        source_types = requested_source_types or plan.preferred_source_types
        search_query = plan.search_query.strip() or plan.query.strip()
        candidates = self._retrieval_query_service.search(
            workspace_id=workspace_id,
            query=search_query,
            source_types=source_types,
            session_id=session_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=search_limit,
        )
        return select_context_sources(
            query=plan.query,
            search_query=search_query,
            candidates=candidates,
            limit=min(self._context_limit, search_limit),
        )
