"""PostgreSQL knowledge document 저장소 구현."""

from __future__ import annotations

from server.app.domain.retrieval import KnowledgeDocument
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
)
from server.app.infrastructure.persistence.postgresql.repositories.retrieval.jsonb import (
    dump_jsonb,
    load_jsonb_object,
)
from server.app.repositories.contracts.retrieval import KnowledgeDocumentRepository


class PostgreSQLKnowledgeDocumentRepository(PostgreSQLRepositoryBase, KnowledgeDocumentRepository):
    """knowledge_documents 테이블 저장소."""

    def upsert(self, document: KnowledgeDocument) -> KnowledgeDocument:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                INSERT INTO knowledge_documents (
                    id,
                    workspace_id,
                    source_type,
                    source_id,
                    session_id,
                    report_id,
                    account_id,
                    contact_id,
                    context_thread_id,
                    title,
                    body,
                    content_hash,
                    metadata_json,
                    created_at,
                    updated_at,
                    indexed_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s::jsonb, %s, %s, %s
                )
                ON CONFLICT (source_type, source_id) DO UPDATE SET
                    workspace_id = EXCLUDED.workspace_id,
                    session_id = EXCLUDED.session_id,
                    report_id = EXCLUDED.report_id,
                    account_id = EXCLUDED.account_id,
                    contact_id = EXCLUDED.contact_id,
                    context_thread_id = EXCLUDED.context_thread_id,
                    title = EXCLUDED.title,
                    body = EXCLUDED.body,
                    content_hash = EXCLUDED.content_hash,
                    metadata_json = EXCLUDED.metadata_json,
                    updated_at = EXCLUDED.updated_at,
                    indexed_at = EXCLUDED.indexed_at
                RETURNING *
                """,
                (
                    document.id,
                    document.workspace_id,
                    document.source_type,
                    document.source_id,
                    document.session_id,
                    document.report_id,
                    document.account_id,
                    document.contact_id,
                    document.context_thread_id,
                    document.title,
                    document.body,
                    document.content_hash,
                    dump_jsonb(document.metadata_json),
                    document.created_at,
                    document.updated_at,
                    document.indexed_at,
                ),
            ).fetchone()
        return self._to_model(row)

    def get_by_source(self, *, source_type: str, source_id: str) -> KnowledgeDocument | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM knowledge_documents
                WHERE source_type = %s AND source_id = %s
                """,
                (source_type, source_id),
            ).fetchone()
        return self._to_model(row) if row is not None else None

    @staticmethod
    def _to_model(row) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=row["id"],
            workspace_id=row["workspace_id"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            session_id=row["session_id"],
            report_id=row["report_id"],
            account_id=row["account_id"],
            contact_id=row["contact_id"],
            context_thread_id=row["context_thread_id"],
            title=row["title"],
            body=row["body"],
            content_hash=row["content_hash"],
            metadata_json=load_jsonb_object(row["metadata_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            indexed_at=row["indexed_at"],
        )
