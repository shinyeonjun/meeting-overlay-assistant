"""knowledge 바운디드 컨텍스트의 공개 API.

다른 컨텍스트와 바깥 계층은 이 패키지만 import한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any


_LAZY_NAMES = {
    "CarryOverService": "server.app.contexts.knowledge.application.history.carry_over_service",
    "HistoryCarryOver": "server.app.contexts.knowledge.application.history.carry_over_service",
    "HistoryQueryService": "server.app.contexts.knowledge.application.history.history_query_service",
    "HistoryRetrievalBrief": "server.app.contexts.knowledge.application.history.history_query_service",
    "MarkdownChunker": "server.app.contexts.knowledge.application.retrieval.chunking.markdown_chunker",
    "OllamaEmbeddingService": "server.app.contexts.knowledge.application.retrieval.embedding.ollama_embedding_service",
    "ReportKnowledgeIndexingService": "server.app.contexts.knowledge.application.retrieval.indexing.report_knowledge_indexing_service",
    "RetrievalQueryService": "server.app.contexts.knowledge.application.retrieval.query.retrieval_query_service",
}

__all__ = [
    "CarryOverService",
    "HistoryCarryOver",
    "HistoryQueryService",
    "HistoryRetrievalBrief",
    "MarkdownChunker",
    "OllamaEmbeddingService",
    "ReportKnowledgeIndexingService",
    "RetrievalQueryService",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_NAMES:
        return getattr(import_module(_LAZY_NAMES[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
