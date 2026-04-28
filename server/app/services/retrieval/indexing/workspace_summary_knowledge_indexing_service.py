"""워크스페이스 노트 인사이트 -> knowledge 인덱싱 서비스."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import KnowledgeDocument
from server.app.repositories.contracts.retrieval import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker
from server.app.services.retrieval.indexing.knowledge_indexing_service import (
    KnowledgeIndexingService,
    KnowledgeSourceDocument,
)
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryDocument,
)


class WorkspaceSummaryKnowledgeIndexingService:
    """노트 인사이트 요약을 공용 retrieval knowledge 계층에 적재한다."""

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

    def index_workspace_summary(
        self,
        document: WorkspaceSummaryDocument,
        *,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> KnowledgeDocument | None:
        """세션별 노트 인사이트 요약을 최신 session_summary 문서로 적재한다."""

        session = self._session_repository.get_by_id(document.session_id)
        if session is None:
            raise ValueError(
                f"knowledge 인덱싱 대상 세션을 찾을 수 없습니다: {document.session_id}"
            )

        body = _render_workspace_summary_markdown(document)
        return self._knowledge_indexing_service.index_source_document(
            KnowledgeSourceDocument(
                workspace_id=workspace_id,
                source_type="session_summary",
                source_id=document.session_id,
                title=_build_document_title(session.title),
                body=body,
                metadata_json={
                    "source_version": document.source_version,
                    "model": document.model,
                    "artifact_kind": "workspace_summary",
                },
                session_id=session.id,
                account_id=session.account_id,
                contact_id=session.contact_id,
                context_thread_id=session.context_thread_id,
            )
        )


def _build_document_title(session_title: str) -> str:
    normalized_title = session_title.strip() or "무제 회의"
    return f"{normalized_title} 노트 인사이트"


def _render_workspace_summary_markdown(document: WorkspaceSummaryDocument) -> str:
    lines: list[str] = [
        "# 노트 인사이트",
        "",
        f"- 세션 ID: {document.session_id}",
        f"- 소스 버전: {document.source_version}",
        f"- 모델: {document.model}",
    ]
    if document.headline:
        lines.extend(["", "## 한 줄 요약", document.headline])
    _append_text_section(lines, "요약", document.summary)
    _append_topic_section(lines, document)
    _append_text_section(lines, "결정 사항", document.decisions)
    _append_action_section(lines, document)
    _append_text_section(lines, "남은 질문", document.open_questions)
    _append_text_section(lines, "이전 회의 대비 변화", document.changed_since_last_meeting)
    return "\n".join(lines).strip()


def _append_text_section(lines: list[str], title: str, items: list[str]) -> None:
    if not items:
        return
    lines.extend(["", f"## {title}"])
    lines.extend(f"- {item}" for item in items if item.strip())


def _append_topic_section(
    lines: list[str],
    document: WorkspaceSummaryDocument,
) -> None:
    if not document.topics:
        return
    lines.extend(["", "## 주제 흐름"])
    for item in document.topics:
        time_range = f" ({item.start_ms}-{item.end_ms}ms)" if item.end_ms else ""
        lines.append(f"- {item.title}{time_range}: {item.summary}")


def _append_action_section(
    lines: list[str],
    document: WorkspaceSummaryDocument,
) -> None:
    if not document.next_actions:
        return
    lines.extend(["", "## 다음 할 일"])
    for item in document.next_actions:
        details = []
        if item.owner:
            details.append(f"담당: {item.owner}")
        if item.due_date:
            details.append(f"기한: {item.due_date}")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"- {item.title}{suffix}")
