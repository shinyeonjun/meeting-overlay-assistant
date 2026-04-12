"""retrieval 저장소 인터페이스 모음."""

from server.app.repositories.contracts.retrieval.knowledge_chunk_repository import (
    KnowledgeChunkRepository,
)
from server.app.repositories.contracts.retrieval.knowledge_document_repository import (
    KnowledgeDocumentRepository,
)

__all__ = [
    "KnowledgeChunkRepository",
    "KnowledgeDocumentRepository",
]
