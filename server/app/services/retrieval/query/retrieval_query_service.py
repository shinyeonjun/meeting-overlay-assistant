"""retrieval 검색 서비스."""

from __future__ import annotations

from collections import OrderedDict
from threading import RLock

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
        embedding_cache_size: int = 256,
    ) -> None:
        self._knowledge_chunk_repository = knowledge_chunk_repository
        self._embedding_service = embedding_service
        self._candidate_limit = candidate_limit
        self._embedding_cache_size = max(0, embedding_cache_size)
        self._embedding_cache: OrderedDict[tuple[str, str], list[float]] = OrderedDict()
        self._embedding_cache_lock = RLock()

    def search(
        self,
        *,
        workspace_id: str,
        query: str,
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalSearchResult]:
        """자연어 질의를 hybrid retrieval로 검색한다."""

        normalized_query = query.strip()
        if not normalized_query:
            return []

        query_embedding = self._embed_query(normalized_query)
        if not query_embedding:
            return []

        return self._knowledge_chunk_repository.search_hybrid(
            workspace_id=workspace_id,
            query_text=normalized_query,
            query_embedding=query_embedding,
            source_types=_normalize_source_types(source_types),
            session_id=session_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
            candidate_limit=self._candidate_limit,
        )

    def _embed_query(self, query: str) -> list[float] | None:
        cache_key = (str(getattr(self._embedding_service, "model", "")), query)
        if self._embedding_cache_size > 0:
            with self._embedding_cache_lock:
                cached = self._embedding_cache.get(cache_key)
                if cached is not None:
                    self._embedding_cache.move_to_end(cache_key)
                    return list(cached)

        embeddings = self._embedding_service.embed([query])
        if not embeddings:
            return None

        embedding = [float(value) for value in embeddings[0]]
        if self._embedding_cache_size > 0:
            with self._embedding_cache_lock:
                self._embedding_cache[cache_key] = embedding
                self._embedding_cache.move_to_end(cache_key)
                while len(self._embedding_cache) > self._embedding_cache_size:
                    self._embedding_cache.popitem(last=False)
        return list(embedding)


def _normalize_source_types(source_types: tuple[str, ...]) -> tuple[str, ...]:
    """검색 범위를 제한할 source_type 목록을 정리한다."""

    normalized: list[str] = []
    seen: set[str] = set()
    for source_type in source_types:
        value = source_type.strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)
