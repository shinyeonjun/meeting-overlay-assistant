"""공통 knowledge 인덱싱 서비스."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from server.app.domain.retrieval import KnowledgeDocument
from server.app.repositories.contracts.retrieval import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker


@dataclass(frozen=True)
class KnowledgeSourceDocument:
    """pgvector knowledge 계층에 적재할 원천 문서."""

    workspace_id: str
    source_type: str
    source_id: str
    title: str
    body: str
    metadata_json: dict[str, object] | None = None
    session_id: str | None = None
    report_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None


class KnowledgeIndexingService:
    """report/transcript/note를 같은 knowledge 테이블에 적재한다."""

    def __init__(
        self,
        *,
        knowledge_document_repository: KnowledgeDocumentRepository,
        knowledge_chunk_repository: KnowledgeChunkRepository,
        embedding_service,
        markdown_chunker: MarkdownChunker,
    ) -> None:
        self._knowledge_document_repository = knowledge_document_repository
        self._knowledge_chunk_repository = knowledge_chunk_repository
        self._embedding_service = embedding_service
        self._markdown_chunker = markdown_chunker

    def index_source_document(
        self,
        source: KnowledgeSourceDocument,
    ) -> KnowledgeDocument | None:
        """원천 문서를 chunk/embedding으로 변환해 pgvector knowledge 계층에 저장한다."""

        normalized_body = source.body.strip()
        if not normalized_body:
            return None

        content_hash = hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()
        existing_document = self._knowledge_document_repository.get_by_source(
            source_type=source.source_type,
            source_id=source.source_id,
        )
        if existing_document is not None and existing_document.content_hash == content_hash:
            return existing_document

        document = KnowledgeDocument.create(
            workspace_id=source.workspace_id,
            source_type=source.source_type,
            source_id=source.source_id,
            title=source.title,
            body=normalized_body,
            content_hash=content_hash,
            metadata_json=source.metadata_json,
            session_id=source.session_id,
            report_id=source.report_id,
            account_id=source.account_id,
            contact_id=source.contact_id,
            context_thread_id=source.context_thread_id,
            existing_id=existing_document.id if existing_document is not None else None,
            created_at=existing_document.created_at if existing_document is not None else None,
        )
        saved_document = self._knowledge_document_repository.upsert(document)

        chunk_drafts = self._markdown_chunker.chunk(normalized_body)
        if not chunk_drafts:
            self._knowledge_chunk_repository.replace_for_document(
                document_id=saved_document.id,
                chunks=[],
            )
            return saved_document

        embeddings = self._embedding_service.embed([item.text for item in chunk_drafts])
        if len(embeddings) != len(chunk_drafts):
            raise RuntimeError("chunk 수와 embedding 수가 일치하지 않습니다.")

        chunks = [
            self._build_chunk(
                document_id=saved_document.id,
                chunk_index=index,
                heading=draft.heading,
                text=draft.text,
                embedding=embeddings[index],
            )
            for index, draft in enumerate(chunk_drafts)
        ]
        self._knowledge_chunk_repository.replace_for_document(
            document_id=saved_document.id,
            chunks=chunks,
        )
        return saved_document

    def _build_chunk(
        self,
        *,
        document_id: str,
        chunk_index: int,
        heading: str | None,
        text: str,
        embedding: list[float],
    ):
        from server.app.domain.retrieval import KnowledgeChunk

        return KnowledgeChunk.create(
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_heading=heading,
            chunk_text=text,
            embedding_model=self._embedding_service.model,
            embedding=embedding,
        )
