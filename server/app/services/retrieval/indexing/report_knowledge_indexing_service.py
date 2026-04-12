"""검색 증강 영역의 report knowledge indexing service 서비스를 제공한다."""
from __future__ import annotations

import hashlib

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import KnowledgeChunk, KnowledgeDocument
from server.app.repositories.contracts.retrieval import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.reports.report_models import BuiltMarkdownReport
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker


class ReportKnowledgeIndexingService:
    """완료된 markdown 리포트를 retrieval knowledge 계층에 적재한다."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        knowledge_document_repository: KnowledgeDocumentRepository,
        knowledge_chunk_repository: KnowledgeChunkRepository,
        embedding_service,
        markdown_chunker: MarkdownChunker,
    ) -> None:
        self._session_repository = session_repository
        self._knowledge_document_repository = knowledge_document_repository
        self._knowledge_chunk_repository = knowledge_chunk_repository
        self._embedding_service = embedding_service
        self._markdown_chunker = markdown_chunker

    def index_markdown_report(
        self,
        built_report: BuiltMarkdownReport,
        *,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> KnowledgeDocument | None:
        """markdown 리포트를 knowledge document/chunk로 적재한다."""

        report = built_report.report
        if report.report_type != "markdown":
            return None

        session = self._session_repository.get_by_id(report.session_id)
        if session is None:
            raise ValueError(f"knowledge 인덱싱 대상 세션을 찾을 수 없습니다: {report.session_id}")

        body = built_report.content.strip()
        if not body:
            return None

        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        existing_document = self._knowledge_document_repository.get_by_source(
            source_type="report",
            source_id=report.id,
        )
        if existing_document is not None and existing_document.content_hash == content_hash:
            return existing_document

        document = KnowledgeDocument.create(
            workspace_id=workspace_id,
            source_type="report",
            source_id=report.id,
            title=self._build_document_title(session.title, report.version),
            body=body,
            content_hash=content_hash,
            session_id=session.id,
            report_id=report.id,
            account_id=session.account_id,
            contact_id=session.contact_id,
            context_thread_id=session.context_thread_id,
            existing_id=existing_document.id if existing_document is not None else None,
            created_at=existing_document.created_at if existing_document is not None else None,
        )
        saved_document = self._knowledge_document_repository.upsert(document)

        chunk_drafts = self._markdown_chunker.chunk(body)
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
            KnowledgeChunk.create(
                document_id=saved_document.id,
                chunk_index=index,
                chunk_heading=draft.heading,
                chunk_text=draft.text,
                embedding_model=self._embedding_service.model,
                embedding=embeddings[index],
            )
            for index, draft in enumerate(chunk_drafts)
        ]
        self._knowledge_chunk_repository.replace_for_document(
            document_id=saved_document.id,
            chunks=chunks,
        )
        return saved_document

    @staticmethod
    def _build_document_title(session_title: str, version: int) -> str:
        normalized_title = session_title.strip() or "무제 회의"
        return f"{normalized_title} 리포트 v{version}"
