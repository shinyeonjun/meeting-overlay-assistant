"""PostgreSQL knowledge chunk 저장소 구현."""

from __future__ import annotations

from server.app.domain.retrieval import KnowledgeChunk, RetrievalSearchResult
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
)
from server.app.infrastructure.persistence.postgresql.repositories.retrieval.jsonb import (
    dump_jsonb,
    load_jsonb_object,
)
from server.app.repositories.contracts.retrieval import KnowledgeChunkRepository


def _format_vector(values: list[float] | tuple[float, ...]) -> str:
    return "[" + ",".join(f"{float(value):.12f}" for value in values) + "]"


class PostgreSQLKnowledgeChunkRepository(PostgreSQLRepositoryBase, KnowledgeChunkRepository):
    """knowledge_chunks 테이블 저장소."""

    def replace_for_document(
        self,
        *,
        document_id: str,
        chunks: list[KnowledgeChunk],
    ) -> list[KnowledgeChunk]:
        with self._database.transaction() as connection:
            connection.execute(
                "DELETE FROM knowledge_chunks WHERE document_id = %s",
                (document_id,),
            )
            for chunk in chunks:
                connection.execute(
                    """
                    INSERT INTO knowledge_chunks (
                        id,
                        document_id,
                        chunk_index,
                        chunk_heading,
                        chunk_text,
                        source_ref,
                        speaker_label,
                        start_ms,
                        end_ms,
                        embedding_model,
                        token_count,
                        char_count,
                        metadata_json,
                        embedding,
                        created_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::jsonb, %s::vector, %s
                    )
                    """,
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.chunk_index,
                        chunk.chunk_heading,
                        chunk.chunk_text,
                        chunk.source_ref,
                        chunk.speaker_label,
                        chunk.start_ms,
                        chunk.end_ms,
                        chunk.embedding_model,
                        chunk.token_count,
                        chunk.char_count,
                        dump_jsonb(chunk.metadata_json),
                        _format_vector(chunk.embedding),
                        chunk.created_at,
                    ),
                )
        return chunks

    def search_hybrid(
        self,
        *,
        workspace_id: str,
        query_text: str,
        query_embedding: list[float],
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 10,
        candidate_limit: int = 100,
    ) -> list[RetrievalSearchResult]:
        filters: list[str] = ["workspace_id = %s"]
        filter_params: list[object] = [workspace_id]

        normalized_source_types = tuple(
            source_type.strip() for source_type in source_types if source_type.strip()
        )
        if normalized_source_types:
            placeholders = ", ".join(["%s"] * len(normalized_source_types))
            filters.append(f"source_type IN ({placeholders})")
            filter_params.extend(normalized_source_types)
        if session_id is not None:
            filters.append("session_id = %s")
            filter_params.append(session_id)
        if account_id is not None:
            filters.append("account_id = %s")
            filter_params.append(account_id)
        if contact_id is not None:
            filters.append("contact_id = %s")
            filter_params.append(contact_id)
        if context_thread_id is not None:
            filters.append("context_thread_id = %s")
            filter_params.append(context_thread_id)

        base_filter_sql = " AND ".join(filters)
        vector_literal = _format_vector(query_embedding)

        if query_text.strip():
            sql = f"""
                WITH lexical_candidates AS MATERIALIZED (
                    SELECT id
                    FROM knowledge_documents
                    WHERE {base_filter_sql}
                      AND search_tsv @@ websearch_to_tsquery('simple', %s)
                    ORDER BY updated_at DESC
                    LIMIT %s
                )
                SELECT
                    kc.id AS chunk_id,
                    kc.document_id,
                    kd.source_type,
                    kd.source_id,
                    kd.title AS document_title,
                    kc.chunk_text,
                    kc.chunk_heading,
                    kc.source_ref,
                    kc.speaker_label,
                    kc.start_ms,
                    kc.end_ms,
                    kc.metadata_json,
                    (kc.embedding <=> %s::vector) AS distance,
                    kd.session_id,
                    kd.report_id,
                    kd.account_id,
                    kd.contact_id,
                    kd.context_thread_id
                FROM knowledge_chunks kc
                JOIN knowledge_documents kd ON kd.id = kc.document_id
                JOIN lexical_candidates lc ON lc.id = kd.id
                ORDER BY kc.embedding <=> %s::vector
                LIMIT %s
            """
            params = [
                *filter_params,
                query_text,
                candidate_limit,
                vector_literal,
                vector_literal,
                limit,
            ]
        else:
            sql = f"""
                SELECT
                    kc.id AS chunk_id,
                    kc.document_id,
                    kd.source_type,
                    kd.source_id,
                    kd.title AS document_title,
                    kc.chunk_text,
                    kc.chunk_heading,
                    kc.source_ref,
                    kc.speaker_label,
                    kc.start_ms,
                    kc.end_ms,
                    kc.metadata_json,
                    (kc.embedding <=> %s::vector) AS distance,
                    kd.session_id,
                    kd.report_id,
                    kd.account_id,
                    kd.contact_id,
                    kd.context_thread_id
                FROM knowledge_chunks kc
                JOIN knowledge_documents kd ON kd.id = kc.document_id
                WHERE {base_filter_sql}
                ORDER BY kc.embedding <=> %s::vector
                LIMIT %s
            """
            params = [vector_literal, *filter_params, vector_literal, limit]

        with self._database.transaction() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [self._to_result(row) for row in rows]

    @staticmethod
    def _to_result(row) -> RetrievalSearchResult:
        return RetrievalSearchResult(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            source_type=row["source_type"],
            source_id=row["source_id"],
            document_title=row["document_title"],
            chunk_text=row["chunk_text"],
            chunk_heading=row["chunk_heading"],
            distance=float(row["distance"]),
            source_ref=row["source_ref"],
            speaker_label=row["speaker_label"],
            start_ms=row["start_ms"],
            end_ms=row["end_ms"],
            metadata_json=load_jsonb_object(row["metadata_json"]),
            session_id=row["session_id"],
            report_id=row["report_id"],
            account_id=row["account_id"],
            contact_id=row["contact_id"],
            context_thread_id=row["context_thread_id"],
        )
