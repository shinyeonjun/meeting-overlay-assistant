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

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


def test_retrieval_query_service_forwards_multiple_session_scope() -> None:
    repository = _FakeKnowledgeChunkRepository()
    service = RetrievalQueryService(
        knowledge_chunk_repository=repository,
        embedding_service=_FakeEmbeddingService(),
        candidate_limit=50,
    )

    service.search(
        workspace_id="workspace-1",
        query="latest meeting decision",
        source_types=("report",),
        session_ids=("session-new", "session-old", "session-new", ""),
        limit=5,
    )

    assert repository.received["session_id"] is None
    assert repository.received["session_ids"] == ("session-new", "session-old")
