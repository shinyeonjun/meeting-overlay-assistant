"""Note transcript knowledge indexing service."""

from __future__ import annotations

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import KnowledgeDocument
from server.app.repositories.contracts.retrieval import (
    KnowledgeChunkRepository,
    KnowledgeDocumentRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.services.reports.refinement import TranscriptCorrectionDocument
from server.app.services.retrieval.chunking.markdown_chunker import MarkdownChunker
from server.app.services.retrieval.indexing.knowledge_indexing_service import (
    KnowledgeIndexingService,
    KnowledgeSourceDocument,
)


class NoteKnowledgeIndexingService:
    """Index the full meeting note transcript as retrieval knowledge."""

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

    def index_note_transcript(
        self,
        *,
        session_id: str,
        source_version: int,
        utterances,
        correction_document: TranscriptCorrectionDocument | None = None,
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> KnowledgeDocument | None:
        """Index all note transcript utterances for one session."""

        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"note knowledge index session not found: {session_id}")

        body = _render_note_transcript_markdown(
            session_id=session.id,
            source_version=source_version,
            utterances=utterances,
            correction_document=correction_document,
        )
        if not body:
            return None

        metadata_json: dict[str, object] = {
            "source_kind": "note",
            "artifact_kind": "note_transcript",
            "source_version": source_version,
        }
        if correction_document is not None:
            metadata_json["correction_model"] = correction_document.model

        return self._knowledge_indexing_service.index_source_document(
            KnowledgeSourceDocument(
                workspace_id=workspace_id,
                source_type="note",
                source_id=_build_canonical_source_id(session.id),
                title=_build_document_title(session.title),
                body=body,
                metadata_json=metadata_json,
                session_id=session.id,
                account_id=session.account_id,
                contact_id=session.contact_id,
                context_thread_id=session.context_thread_id,
            )
        )


def _render_note_transcript_markdown(
    *,
    session_id: str,
    source_version: int,
    utterances,
    correction_document: TranscriptCorrectionDocument | None,
) -> str:
    correction_map = {
        item.utterance_id: item
        for item in (correction_document.items if correction_document is not None else [])
    }
    transcript_lines: list[str] = []
    for utterance in sorted(utterances, key=lambda item: (item.seq_num, item.start_ms)):
        correction = correction_map.get(utterance.id)
        text = (
            correction.corrected_text.strip()
            if correction is not None and correction.corrected_text.strip()
            else utterance.text.strip()
        )
        if not text:
            continue
        transcript_lines.append(
            "- "
            f"[{_format_ms(utterance.start_ms)}-{_format_ms(utterance.end_ms)}] "
            f"{utterance.speaker_label or 'speaker-unknown'}: {text}"
        )

    if not transcript_lines:
        return ""

    lines = [
        "# Note transcript",
        "",
        f"- Session ID: {session_id}",
        f"- Source version: {source_version}",
    ]
    if correction_document is not None:
        lines.append(f"- Correction model: {correction_document.model}")
    lines.extend(["", "## Transcript", *transcript_lines])
    return "\n".join(lines).strip()


def _build_document_title(session_title: str) -> str:
    normalized_title = session_title.strip() or "Untitled meeting"
    return f"{normalized_title} note transcript"


def _build_canonical_source_id(session_id: str) -> str:
    return f"session:{session_id}:latest-note"


def _format_ms(value: int | None) -> str:
    if value is None:
        return "??:??"
    total_seconds = max(0, int(value) // 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"
