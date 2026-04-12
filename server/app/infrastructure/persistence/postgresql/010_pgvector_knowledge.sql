-- CAPS pgvector 1차 설계 초안
-- 목표:
-- 1. PostgreSQL 정본 위에 retrieval / memory 계층을 얹는다.
-- 2. 1차는 report 중심 knowledge 적재만 다룬다.
-- 3. 현재 runtime-compatible schema(sessions, reports, accounts, contacts, context_threads)와 바로 연결한다.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_type TEXT NOT NULL
        CHECK (source_type IN ('report', 'history_carry_over', 'session_summary')),
    source_id TEXT NOT NULL,
    session_id TEXT,
    report_id TEXT,
    account_id TEXT,
    contact_id TEXT,
    context_thread_id TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', CONCAT_WS(' ', COALESCE(title, ''), COALESCE(body, '')))
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    indexed_at TIMESTAMPTZ,
    UNIQUE (source_type, source_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_heading TEXT,
    chunk_text TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    char_count INTEGER NOT NULL DEFAULT 0 CHECK (char_count >= 0),
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_workspace_source
    ON knowledge_documents(workspace_id, source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_session_updated
    ON knowledge_documents(session_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_report_id
    ON knowledge_documents(report_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_account_created
    ON knowledge_documents(account_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_contact_created
    ON knowledge_documents(contact_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_thread_created
    ON knowledge_documents(context_thread_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS gin_knowledge_documents_search_tsv
    ON knowledge_documents USING GIN (search_tsv);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge_chunks(document_id, chunk_index);

-- HNSW를 우선으로 본다.
-- 운영 환경의 pgvector 버전 제약으로 HNSW 사용이 어렵다면 IVFFlat 대체를 검토한다.
CREATE INDEX IF NOT EXISTS hnsw_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

ALTER TABLE knowledge_documents
    DROP COLUMN IF EXISTS search_tsv,
    DROP COLUMN IF EXISTS search_text;

ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', CONCAT_WS(' ', COALESCE(title, ''), COALESCE(body, '')))
    ) STORED;

ALTER TABLE knowledge_documents
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::text::timestamptz,
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at::text::timestamptz,
    ALTER COLUMN indexed_at TYPE TIMESTAMPTZ USING NULLIF(indexed_at::text, '')::timestamptz;

ALTER TABLE knowledge_chunks
    ALTER COLUMN embedding TYPE VECTOR(768) USING embedding::text::vector(768),
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at::text::timestamptz;
