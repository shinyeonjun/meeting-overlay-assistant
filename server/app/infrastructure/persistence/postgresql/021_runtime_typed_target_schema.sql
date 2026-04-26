-- CAPS PostgreSQL 2차 타입 개선 정본 스키마
-- 목표:
-- 1. 현재 runtime 테이블 이름과 핵심 컬럼 계약은 유지한다.
-- 2. 식별자/시간/범주형 컬럼 타입을 PostgreSQL 친화적으로 정리한다.
-- 3. 이 파일은 fresh schema 기준안이며, 현재 runtime DB에 대한 직접 migration 스크립트는 아니다.
-- 4. 현재 runtime-compatible 스키마(020)와 분리해 2차 설계 기준점으로 사용한다.

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS vector;

-- 워크스페이스 / 사용자 / 인증
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    login_id CITEXT NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    job_title VARCHAR(120),
    department VARCHAR(120),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    workspace_role VARCHAR(32) NOT NULL DEFAULT 'member',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    joined_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auth_password_credentials (
    user_id UUID PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    password_updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    client_type VARCHAR(32) NOT NULL DEFAULT 'desktop',
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 맥락
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    account_id UUID,
    name VARCHAR(120) NOT NULL,
    email CITEXT,
    job_title VARCHAR(120),
    department VARCHAR(120),
    notes TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS context_threads (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    account_id UUID,
    contact_id UUID,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 세션 / 참여자
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    account_id UUID,
    contact_id UUID,
    context_thread_id UUID,
    primary_input_source VARCHAR(32) NOT NULL,
    actual_active_sources JSONB NOT NULL DEFAULT '[]'::JSONB,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    recovery_required BOOLEAN NOT NULL DEFAULT FALSE,
    recovery_reason TEXT,
    recovery_detected_at TIMESTAMPTZ,
    recording_artifact_id TEXT,
    post_processing_status VARCHAR(32) NOT NULL DEFAULT 'not_started',
    post_processing_error_message TEXT,
    post_processing_requested_at TIMESTAMPTZ,
    post_processing_started_at TIMESTAMPTZ,
    post_processing_completed_at TIMESTAMPTZ,
    canonical_transcript_version INTEGER NOT NULL DEFAULT 0,
    canonical_events_version INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS session_participants (
    session_id UUID NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name VARCHAR(120) NOT NULL,
    normalized_participant_name VARCHAR(120) NOT NULL,
    participant_email CITEXT,
    participant_job_title VARCHAR(120),
    participant_department VARCHAR(120),
    resolution_status VARCHAR(32) NOT NULL DEFAULT 'unmatched',
    contact_id UUID,
    account_id UUID,
    PRIMARY KEY (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS participant_followups (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name VARCHAR(120) NOT NULL,
    resolution_status VARCHAR(32) NOT NULL,
    followup_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    matched_contact_count INTEGER NOT NULL DEFAULT 0 CHECK (matched_contact_count >= 0),
    contact_id UUID,
    account_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    resolved_by_user_id UUID,
    UNIQUE (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 회의록 / 배치 작업
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    report_type VARCHAR(32) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    file_artifact_id TEXT,
    file_path TEXT NOT NULL,
    insight_source VARCHAR(32) NOT NULL DEFAULT 'live_fallback',
    generated_by_user_id UUID,
    generated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (session_id, report_type, version),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS session_post_processing_jobs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    recording_artifact_id TEXT,
    recording_path TEXT,
    error_message TEXT,
    requested_by_user_id UUID,
    claimed_by_worker_id VARCHAR(120),
    lease_expires_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS note_correction_jobs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    source_version INTEGER NOT NULL DEFAULT 0 CHECK (source_version >= 0),
    status VARCHAR(32) NOT NULL,
    error_message TEXT,
    requested_by_user_id UUID,
    claimed_by_worker_id VARCHAR(120),
    lease_expires_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS report_generation_jobs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    recording_artifact_id TEXT,
    recording_path TEXT,
    transcript_path TEXT,
    markdown_report_id UUID,
    pdf_report_id UUID,
    error_message TEXT,
    requested_by_user_id UUID,
    claimed_by_worker_id VARCHAR(120),
    lease_expires_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (markdown_report_id) REFERENCES reports(id) ON DELETE SET NULL,
    FOREIGN KEY (pdf_report_id) REFERENCES reports(id) ON DELETE SET NULL,
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS report_shares (
    id UUID PRIMARY KEY,
    report_id UUID NOT NULL,
    shared_by_user_id UUID,
    shared_with_user_id UUID NOT NULL,
    permission VARCHAR(16) NOT NULL DEFAULT 'view',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (shared_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- STT / 화면 / 이벤트
CREATE TABLE IF NOT EXISTS utterances (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    seq_num INTEGER NOT NULL,
    start_ms BIGINT NOT NULL,
    end_ms BIGINT NOT NULL,
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    input_source VARCHAR(32),
    stt_backend VARCHAR(80),
    latency_ms INTEGER,
    speaker_label VARCHAR(120),
    transcript_source VARCHAR(32) NOT NULL DEFAULT 'live',
    processing_job_id UUID,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (processing_job_id) REFERENCES session_post_processing_jobs(id) ON DELETE SET NULL,
    CONSTRAINT uq_utterances_session_seq UNIQUE (session_id, seq_num)
);

CREATE TABLE IF NOT EXISTS overlay_events (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    source_utterance_id UUID,
    event_type VARCHAR(32) NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT,
    body TEXT,
    evidence_text TEXT,
    speaker_label VARCHAR(120),
    state VARCHAR(32) NOT NULL,
    input_source VARCHAR(32),
    insight_scope VARCHAR(32) NOT NULL DEFAULT 'live',
    event_source VARCHAR(32) NOT NULL DEFAULT 'live',
    processing_job_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    finalized_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (source_utterance_id) REFERENCES utterances(id) ON DELETE SET NULL,
    FOREIGN KEY (processing_job_id) REFERENCES session_post_processing_jobs(id) ON DELETE SET NULL
);

-- Retrieval / knowledge
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    source_type VARCHAR(32) NOT NULL
        CHECK (source_type IN ('report', 'history_carry_over', 'session_summary')),
    source_id VARCHAR(255) NOT NULL,
    session_id UUID,
    report_id UUID,
    account_id UUID,
    contact_id UUID,
    context_thread_id UUID,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    content_hash VARCHAR(128) NOT NULL,
    search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(body, ''))
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
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_heading VARCHAR(255),
    chunk_text TEXT NOT NULL,
    embedding_model VARCHAR(120) NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    char_count INTEGER NOT NULL DEFAULT 0 CHECK (char_count >= 0),
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
);

-- 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS uq_report_shares_report_recipient
    ON report_shares(report_id, shared_with_user_id);

CREATE INDEX IF NOT EXISTS idx_utterances_session_seq
    ON utterances(session_id, seq_num);

CREATE INDEX IF NOT EXISTS idx_overlay_events_session_type
    ON overlay_events(session_id, event_type, state);

CREATE INDEX IF NOT EXISTS idx_overlay_events_session_created
    ON overlay_events(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_overlay_events_source_utterance
    ON overlay_events(session_id, source_utterance_id, created_at);

CREATE INDEX IF NOT EXISTS idx_reports_session_generated
    ON reports(session_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_session_post_processing_jobs_session_created
    ON session_post_processing_jobs(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_session_post_processing_jobs_status_created
    ON session_post_processing_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS idx_session_post_processing_jobs_claimable
    ON session_post_processing_jobs(status, lease_expires_at, created_at);

CREATE INDEX IF NOT EXISTS idx_note_correction_jobs_session_created
    ON note_correction_jobs(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_note_correction_jobs_status_created
    ON note_correction_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS idx_note_correction_jobs_claimable
    ON note_correction_jobs(status, lease_expires_at, created_at);

CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_session_created
    ON report_generation_jobs(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_status_created
    ON report_generation_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS idx_report_generation_jobs_claimable
    ON report_generation_jobs(status, lease_expires_at, created_at);

CREATE INDEX IF NOT EXISTS idx_report_shares_report_created
    ON report_shares(report_id, created_at);

CREATE INDEX IF NOT EXISTS idx_report_shares_recipient_created
    ON report_shares(shared_with_user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_sessions_status_started
    ON sessions(status, started_at);

CREATE INDEX IF NOT EXISTS idx_sessions_created_by_user
    ON sessions(created_by_user_id, started_at);

CREATE INDEX IF NOT EXISTS idx_sessions_account_started
    ON sessions(account_id, started_at);

CREATE INDEX IF NOT EXISTS idx_sessions_contact_started
    ON sessions(contact_id, started_at);

CREATE INDEX IF NOT EXISTS idx_sessions_context_thread_started
    ON sessions(context_thread_id, started_at);

CREATE INDEX IF NOT EXISTS idx_sessions_post_processing_status_started
    ON sessions(post_processing_status, started_at);

CREATE INDEX IF NOT EXISTS idx_session_participants_session_order
    ON session_participants(session_id, participant_order);

CREATE INDEX IF NOT EXISTS idx_session_participants_contact
    ON session_participants(contact_id, session_id);

CREATE INDEX IF NOT EXISTS idx_session_participants_account_normalized_name
    ON session_participants(account_id, normalized_participant_name);

CREATE INDEX IF NOT EXISTS idx_session_participants_resolution_status
    ON session_participants(resolution_status, session_id);

CREATE INDEX IF NOT EXISTS idx_participant_followups_session_status
    ON participant_followups(session_id, followup_status, participant_order);

CREATE INDEX IF NOT EXISTS idx_participant_followups_status_created
    ON participant_followups(followup_status, created_at);

CREATE INDEX IF NOT EXISTS idx_participant_followups_contact_status
    ON participant_followups(contact_id, followup_status);

CREATE INDEX IF NOT EXISTS idx_users_login_id
    ON users(login_id);

CREATE INDEX IF NOT EXISTS idx_workspace_members_user_status
    ON workspace_members(user_id, status);

CREATE INDEX IF NOT EXISTS idx_workspace_members_role
    ON workspace_members(workspace_id, workspace_role, status);

CREATE INDEX IF NOT EXISTS idx_accounts_workspace_name
    ON accounts(workspace_id, name);

CREATE INDEX IF NOT EXISTS idx_contacts_workspace_account_name
    ON contacts(workspace_id, account_id, name);

CREATE INDEX IF NOT EXISTS idx_context_threads_workspace_updated
    ON context_threads(workspace_id, updated_at);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
    ON auth_sessions(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires
    ON auth_sessions(expires_at);

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

CREATE INDEX IF NOT EXISTS hnsw_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
