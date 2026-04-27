from server.app.domain.models.report import Report
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.services.reports.report_models import BuiltMarkdownReport
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker
from server.app.services.retrieval.indexing.knowledge_indexing_service import (
    KnowledgeIndexingService,
    KnowledgeSourceDocument,
)
from server.app.services.retrieval.indexing.report_knowledge_indexing_service import (
    ReportKnowledgeIndexingService,
)


class _FakeSessionRepository:
    def __init__(self, session: MeetingSession) -> None:
        self._session = session

    def get_by_id(self, session_id: str) -> MeetingSession | None:
        if session_id == self._session.id:
            return self._session
        return None


class _FakeKnowledgeDocumentRepository:
    def __init__(self) -> None:
        self.saved = None
        self.existing = None

    def upsert(self, document):
        self.saved = document
        self.existing = document
        return document

    def get_by_source(self, *, source_type: str, source_id: str):
        if self.existing and self.existing.source_type == source_type and self.existing.source_id == source_id:
            return self.existing
        return None


class _FakeKnowledgeChunkRepository:
    def __init__(self) -> None:
        self.replaced_document_id = None
        self.chunks = []

    def replace_for_document(self, *, document_id: str, chunks: list):
        self.replaced_document_id = document_id
        self.chunks = chunks
        return chunks


class _FakeEmbeddingService:
    model = "fake-embedding-model"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index + 1), 0.5] for index, _ in enumerate(texts)]


def test_report_knowledge_indexing_service_indexes_markdown_report() -> None:
    session = MeetingSession.create_draft(
        title="보안 검토 회의",
        mode=SessionMode.MEETING,
        source=AudioSource.MIC,
        account_id="account-1",
        contact_id="contact-1",
        context_thread_id="thread-1",
    )
    report_content = "# 요약\n\n보안 검토 필요\n\n- 다음 주에 재확인"
    report = Report.create(
        session_id=session.id,
        report_type="markdown",
        version=1,
        file_path="D:/caps/server/data/reports/sample.md",
        insight_source="high_precision_audio",
    )
    built_report = BuiltMarkdownReport(
        report=report,
        content=report_content,
        speaker_transcript=[],
        speaker_events=[],
    )
    document_repository = _FakeKnowledgeDocumentRepository()
    chunk_repository = _FakeKnowledgeChunkRepository()
    service = ReportKnowledgeIndexingService(
        session_repository=_FakeSessionRepository(session),
        knowledge_document_repository=document_repository,
        knowledge_chunk_repository=chunk_repository,
        embedding_service=_FakeEmbeddingService(),
        markdown_chunker=MarkdownChunker(target_chars=60, overlap_chars=10),
    )

    saved_document = service.index_markdown_report(built_report)

    assert saved_document is not None
    assert saved_document.report_id == report.id
    assert saved_document.account_id == "account-1"
    assert chunk_repository.replaced_document_id == saved_document.id
    assert len(chunk_repository.chunks) >= 1
    assert all(chunk.embedding_model == "fake-embedding-model" for chunk in chunk_repository.chunks)


def test_knowledge_indexing_service가_note와_transcript_source_type도_저장할_수_있다() -> None:
    document_repository = _FakeKnowledgeDocumentRepository()
    chunk_repository = _FakeKnowledgeChunkRepository()
    service = KnowledgeIndexingService(
        knowledge_document_repository=document_repository,
        knowledge_chunk_repository=chunk_repository,
        embedding_service=_FakeEmbeddingService(),
        markdown_chunker=MarkdownChunker(target_chars=80, overlap_chars=10),
    )

    saved_document = service.index_source_document(
        KnowledgeSourceDocument(
            workspace_id="workspace-1",
            source_type="note",
            source_id="note-1",
            title="회의 후 개인 노트",
            body="# 메모\n\n결제 라우팅 수정안과 QA 범위를 다시 확인해야 한다.",
            metadata_json={"feature": "note_analysis"},
            session_id="session-1",
            account_id="account-1",
            contact_id="contact-1",
            context_thread_id="thread-1",
        )
    )

    assert saved_document is not None
    assert saved_document.source_type == "note"
    assert saved_document.source_id == "note-1"
    assert saved_document.metadata_json == {"feature": "note_analysis"}
    assert saved_document.report_id is None
    assert saved_document.session_id == "session-1"
    assert chunk_repository.replaced_document_id == saved_document.id
    assert len(chunk_repository.chunks) == 1
