"""knowledge document 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.retrieval import KnowledgeDocument


class KnowledgeDocumentRepository(ABC):
    """knowledge document 저장/조회 계약."""

    @abstractmethod
    def upsert(self, document: KnowledgeDocument) -> KnowledgeDocument:
        raise NotImplementedError

    @abstractmethod
    def get_by_source(self, *, source_type: str, source_id: str) -> KnowledgeDocument | None:
        raise NotImplementedError
