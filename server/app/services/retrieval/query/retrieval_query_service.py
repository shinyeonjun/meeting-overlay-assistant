"""검색 증강 영역의 retrieval query service 서비스를 제공한다."""
from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.repositories.contracts.retrieval import KnowledgeChunkRepository


class RetrievalQueryService:
    """FTS + pgvector hybrid retrieval 조회를 제공한다."""

    def __init__(
        self,
        *,
        knowledge_chunk_repository: KnowledgeChunkRepository,
        embedding_service,
        candidate_limit: int = 100,
    ) -> None:
        self._knowledge_chunk_repository = knowledge_chunk_repository
        self._embedding_service = embedding_service
        self._candidate_limit = candidate_limit

    def search(
        self,
        *,
        workspace_id: str,
        query: str,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalSearchResult]:
        """자연어 질의를 hybrid retrieval로 검색한다."""

        normalized_query = query.strip()
        if not normalized_query:
            return []

        embeddings = self._embedding_service.embed([normalized_query])
        if not embeddings:
            return []

        return self._knowledge_chunk_repository.search_hybrid(
            workspace_id=workspace_id,
            query_text=normalized_query,
            query_embedding=embeddings[0],
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
            candidate_limit=self._candidate_limit,
        )
