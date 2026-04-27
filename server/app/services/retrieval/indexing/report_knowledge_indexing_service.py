"""회의록 -> knowledge 인덱싱 서비스."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import KnowledgeDocument
from server.app.repositories.contracts.retrieval import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.reports.report_models import BuiltMarkdownReport
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker
from server.app.services.retrieval.indexing.knowledge_indexing_service import (
    KnowledgeIndexingService,
    KnowledgeSourceDocument,
)


class ReportKnowledgeIndexingService:
    """완료된 markdown 회의록을 retrieval knowledge 계층에 적재한다."""

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
        self._knowledge_indexing_service = KnowledgeIndexingService(
            knowledge_document_repository=knowledge_document_repository,
            knowledge_chunk_repository=knowledge_chunk_repository,
            embedding_service=embedding_service,
            markdown_chunker=markdown_chunker,
        )

    def index_markdown_report(
        self,
        built_report: BuiltMarkdownReport,
        *,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> KnowledgeDocument | None:
        """markdown 회의록을 knowledge document/chunk로 적재한다."""

        report = built_report.report
        if report.report_type != "markdown":
            return None

        session = self._session_repository.get_by_id(report.session_id)
        if session is None:
            raise ValueError(f"knowledge 인덱싱 대상 세션을 찾을 수 없습니다: {report.session_id}")

        return self._knowledge_indexing_service.index_source_document(
            KnowledgeSourceDocument(
                workspace_id=workspace_id,
                source_type="report",
                source_id=report.id,
                title=self._build_document_title(session.title, report.version),
                body=built_report.content,
                session_id=session.id,
                report_id=report.id,
                account_id=session.account_id,
                contact_id=session.contact_id,
                context_thread_id=session.context_thread_id,
            )
        )

    @staticmethod
    def _build_document_title(session_title: str, version: int) -> str:
        normalized_title = session_title.strip() or "무제 회의"
        return f"{normalized_title} 회의록 v{version}"
