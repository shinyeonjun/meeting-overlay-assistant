"""PostgreSQL retrieval 저장소 모음."""

from server.app.infrastructure.persistence.postgresql.repositories.retrieval.postgresql_knowledge_chunk_repository import (
    PostgreSQLKnowledgeChunkRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.retrieval.postgresql_knowledge_document_repository import (
    PostgreSQLKnowledgeDocumentRepository,
)

__all__ = [
    "PostgreSQLKnowledgeChunkRepository",
    "PostgreSQLKnowledgeDocumentRepository",
]
