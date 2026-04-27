"""knowledge chunk 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.retrieval import KnowledgeChunk, RetrievalSearchResult


class KnowledgeChunkRepository(ABC):
    """knowledge chunk 저장/검색 계약."""

    @abstractmethod
    def replace_for_document(
        self,
        *,
        document_id: str,
        chunks: list[KnowledgeChunk],
    ) -> list[KnowledgeChunk]:
        raise NotImplementedError

    @abstractmethod
    def search_hybrid(
        self,
        *,
        workspace_id: str,
        query_text: str,
        query_embedding: list[float],
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 10,
        candidate_limit: int = 100,
    ) -> list[RetrievalSearchResult]:
        raise NotImplementedError
