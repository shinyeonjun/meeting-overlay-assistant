"""retrieval query service 테스트."""

from server.app.services.retrieval.query.retrieval_query_service import RetrievalQueryService


class _FakeKnowledgeChunkRepository:
    def __init__(self) -> None:
        self.received = None

    def replace_for_document(self, *, document_id: str, chunks: list):
        return chunks

    def has_chunks_for_signature(self, *, document_id: str, chunker_signature: str) -> bool:
        return False

    def search_hybrid(self, **kwargs):
        self.received = kwargs
        return []


class _FakeEmbeddingService:
    model = "fake-embedding"

    def __init__(self) -> None:
        self.calls = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(tuple(texts))
        return [[0.1, 0.2] for _ in texts]


def test_retrieval_query_service가_source_type과_session_scope를_전달한다() -> None:
    repository = _FakeKnowledgeChunkRepository()
    embedding_service = _FakeEmbeddingService()
    service = RetrievalQueryService(
        knowledge_chunk_repository=repository,
        embedding_service=embedding_service,
        candidate_limit=50,
    )

    result = service.search(
        workspace_id="workspace-1",
        query="결제 라우팅",
        source_types=("report", "note", "report", ""),
        session_id="session-1",
        limit=5,
    )

    assert result == []
    assert repository.received["source_types"] == ("report", "note")
    assert repository.received["session_id"] == "session-1"
    assert repository.received["candidate_limit"] == 50


def test_retrieval_query_service는_같은_질문의_embedding을_재사용한다() -> None:
    repository = _FakeKnowledgeChunkRepository()
    embedding_service = _FakeEmbeddingService()
    service = RetrievalQueryService(
        knowledge_chunk_repository=repository,
        embedding_service=embedding_service,
        candidate_limit=50,
    )

    for _ in range(2):
        service.search(
            workspace_id="workspace-1",
            query="결제 라우팅",
            source_types=("report",),
            limit=5,
        )

    assert embedding_service.calls == [("결제 라우팅",)]
