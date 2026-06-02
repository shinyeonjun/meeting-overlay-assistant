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
        filters: list[str] = ["kd.workspace_id = %s"]
        filter_params: list[object] = [workspace_id]

        normalized_source_types = tuple(
            source_type.strip() for source_type in source_types if source_type.strip()
        )
        if normalized_source_types:
            placeholders = ", ".join(["%s"] * len(normalized_source_types))
            filters.append(f"kd.source_type IN ({placeholders})")
            filter_params.extend(normalized_source_types)
        if session_id is not None:
            filters.append("kd.session_id = %s")
            filter_params.append(session_id)
        if account_id is not None:
            filters.append("kd.account_id = %s")
            filter_params.append(account_id)
        if contact_id is not None:
            filters.append("kd.contact_id = %s")
            filter_params.append(contact_id)
        if context_thread_id is not None:
            filters.append("kd.context_thread_id = %s")
            filter_params.append(context_thread_id)

        base_filter_sql = " AND ".join(filters)
        vector_literal = _format_vector(query_embedding)
        normalized_query = query_text.strip()

        if normalized_query:
            sql = f"""
                WITH lexical_query AS MATERIALIZED (
                    SELECT websearch_to_tsquery('simple', %s) AS tsq
                ),
                vector_candidates AS MATERIALIZED (
                    SELECT
                        ranked.chunk_id,
                        ranked.distance,
                        ROW_NUMBER() OVER (ORDER BY ranked.distance ASC) AS vector_rank
                    FROM (
                        SELECT
                            kc.id AS chunk_id,
                            (kc.embedding <=> %s::vector) AS distance
                        FROM knowledge_chunks kc
                        JOIN knowledge_documents kd ON kd.id = kc.document_id
                        WHERE {base_filter_sql}
                        ORDER BY kc.embedding <=> %s::vector
                        LIMIT %s
                    ) ranked
                ),
                lexical_ranked AS MATERIALIZED (
                    SELECT
                        kc.id AS chunk_id,
                        (kc.embedding <=> %s::vector) AS distance,
                        ts_rank_cd(
                            to_tsvector(
                                'simple',
                                COALESCE(kc.chunk_heading, '') || ' ' || COALESCE(kc.chunk_text, '')
                            ),
                            lq.tsq
                        ) AS lexical_score,
                        kd.updated_at,
                        kc.chunk_index
                    FROM knowledge_chunks kc
                    JOIN knowledge_documents kd ON kd.id = kc.document_id
                    CROSS JOIN lexical_query lq
                    WHERE {base_filter_sql}
                      AND (
                          kd.search_tsv @@ lq.tsq
                          OR to_tsvector(
                              'simple',
                              COALESCE(kc.chunk_heading, '') || ' ' || COALESCE(kc.chunk_text, '')
                          ) @@ lq.tsq
                      )
                ),
                lexical_candidates AS MATERIALIZED (
                    SELECT
                        ranked.chunk_id,
                        ranked.distance,
                        ROW_NUMBER() OVER (
                            ORDER BY ranked.lexical_score DESC, ranked.updated_at DESC, ranked.chunk_index ASC
                        ) AS lexical_rank
                    FROM lexical_ranked ranked
                    ORDER BY ranked.lexical_score DESC, ranked.updated_at DESC, ranked.chunk_index ASC
                    LIMIT %s
                ),
                candidate_chunks AS (
                    SELECT
                        COALESCE(vc.chunk_id, lc.chunk_id) AS chunk_id,
                        LEAST(
                            COALESCE(vc.distance, lc.distance),
                            COALESCE(lc.distance, vc.distance)
                        ) AS distance,
                        (
                            CASE
                                WHEN vc.vector_rank IS NULL THEN 0.0
                                ELSE 1.0 / (60.0 + vc.vector_rank)
                            END
                            +
                            CASE
                                WHEN lc.lexical_rank IS NULL THEN 0.0
                                ELSE 1.0 / (60.0 + lc.lexical_rank)
                            END
                        ) AS rank_score
                    FROM vector_candidates vc
                    FULL OUTER JOIN lexical_candidates lc ON lc.chunk_id = vc.chunk_id
                )
                {self._select_candidate_chunks_sql()}
                ORDER BY cc.rank_score DESC, cc.distance ASC, kd.updated_at DESC
                LIMIT %s
            """
            params = [
                normalized_query,
                vector_literal,
                *filter_params,
                vector_literal,
                candidate_limit,
                vector_literal,
                *filter_params,
                candidate_limit,
                limit,
            ]
        else:
            sql = f"""
                WITH candidate_chunks AS MATERIALIZED (
                    SELECT
                        kc.id AS chunk_id,
                        (kc.embedding <=> %s::vector) AS distance,
                        1.0 / (60.0 + ROW_NUMBER() OVER (ORDER BY kc.embedding <=> %s::vector)) AS rank_score
                    FROM knowledge_chunks kc
                    JOIN knowledge_documents kd ON kd.id = kc.document_id
                    WHERE {base_filter_sql}
                    ORDER BY kc.embedding <=> %s::vector
                    LIMIT %s
                )
                {self._select_candidate_chunks_sql()}
                ORDER BY cc.distance ASC, kd.updated_at DESC
                LIMIT %s
            """
            params = [
                vector_literal,
                vector_literal,
                *filter_params,
                vector_literal,
                candidate_limit,
                limit,
            ]

        with self._database.transaction() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [self._to_result(row) for row in rows]

    @staticmethod
    def _select_candidate_chunks_sql() -> str:
        return """
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
                cc.distance AS distance,
                cc.rank_score AS rank_score,
                kd.session_id,
                kd.report_id,
                kd.account_id,
                kd.contact_id,
                kd.context_thread_id
            FROM candidate_chunks cc
            JOIN knowledge_chunks kc ON kc.id = cc.chunk_id
            JOIN knowledge_documents kd ON kd.id = kc.document_id
        """

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
            rank_score=float(row["rank_score"]) if row["rank_score"] is not None else None,
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
