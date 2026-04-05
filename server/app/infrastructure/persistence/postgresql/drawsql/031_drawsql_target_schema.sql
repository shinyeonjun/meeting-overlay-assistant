-- CAPS DrawSQL 목표 구조 스키마
-- 목적:
-- 1. 현재 문자열 ID 대신 UUID 기반 목표 구조를 시각화한다.
-- 2. 시간/숫자/JSON/vector 타입을 스키마에 맞게 분리한다.
-- 3. DrawSQL import 호환성을 위해 enum 대신 VARCHAR 범주 컬럼만 둔다.
-- 4. 현재 호환 스키마 문맥에 남아 있는 중복/호환 컬럼은 가능한 한 제거한다.

CREATE TABLE workspaces (
    id UUID PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE users (
    id UUID PRIMARY KEY,
    login_id VARCHAR(120) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    job_title VARCHAR(120),
    department VARCHAR(120),
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE workspace_members (
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    workspace_role VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE auth_password_credentials (
    user_id UUID PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    password_updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    client_type VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    account_id UUID,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(320),
    job_title VARCHAR(120),
    department VARCHAR(120),
    notes TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE context_threads (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    account_id UUID,
    contact_id UUID,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    created_by_user_id UUID,
    account_id UUID,
    contact_id UUID,
    context_thread_id UUID,
    primary_input_source VARCHAR(32) NOT NULL,
    actual_active_sources JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    recording_artifact_id VARCHAR(255),
    post_processing_status VARCHAR(32) NOT NULL,
    post_processing_error_message TEXT,
    post_processing_requested_at TIMESTAMPTZ,
    post_processing_started_at TIMESTAMPTZ,
    post_processing_completed_at TIMESTAMPTZ,
    canonical_transcript_version INTEGER NOT NULL,
    canonical_events_version INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id)
);

CREATE TABLE session_participants (
    session_id UUID NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name VARCHAR(120) NOT NULL,
    normalized_participant_name VARCHAR(120) NOT NULL,
    participant_email VARCHAR(320),
    participant_job_title VARCHAR(120),
    participant_department VARCHAR(120),
    resolution_status VARCHAR(32) NOT NULL,
    contact_id UUID,
    account_id UUID,
    PRIMARY KEY (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE participant_followups (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name VARCHAR(120) NOT NULL,
    resolution_status VARCHAR(32) NOT NULL,
    followup_status VARCHAR(32) NOT NULL,
    matched_contact_count INTEGER NOT NULL,
    contact_id UUID,
    account_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    resolved_by_user_id UUID,
    UNIQUE (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id)
);

CREATE TABLE utterances (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    seq_num INTEGER NOT NULL,
    start_ms BIGINT NOT NULL,
    end_ms BIGINT NOT NULL,
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    input_source VARCHAR(32),
    stt_backend VARCHAR(80),
    latency_ms INTEGER,
    speaker_label VARCHAR(120),
    transcript_source VARCHAR(32) NOT NULL,
    processing_job_id VARCHAR(255),
    UNIQUE (session_id, seq_num),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE overlay_events (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    source_utterance_id UUID,
    event_type VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    normalized_title VARCHAR(255),
    body TEXT,
    evidence_text TEXT,
    speaker_label VARCHAR(120),
    state VARCHAR(32) NOT NULL,
    input_source VARCHAR(32),
    insight_scope VARCHAR(32) NOT NULL,
    event_source VARCHAR(32) NOT NULL,
    processing_job_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    finalized_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (source_utterance_id) REFERENCES utterances(id)
);

CREATE TABLE reports (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    report_type VARCHAR(32) NOT NULL,
    version INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    insight_source VARCHAR(32) NOT NULL,
    generated_by_user_id UUID,
    generated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (session_id, report_type, version),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (generated_by_user_id) REFERENCES users(id)
);

CREATE TABLE report_generation_jobs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    recording_path TEXT,
    transcript_path TEXT,
    markdown_report_id UUID,
    pdf_report_id UUID,
    error_message TEXT,
    requested_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (markdown_report_id) REFERENCES reports(id),
    FOREIGN KEY (pdf_report_id) REFERENCES reports(id),
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id)
);

CREATE TABLE session_post_processing_jobs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    recording_path TEXT,
    error_message TEXT,
    requested_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id)
);

CREATE TABLE report_shares (
    id UUID PRIMARY KEY,
    report_id UUID NOT NULL,
    shared_by_user_id UUID NOT NULL,
    shared_with_user_id UUID NOT NULL,
    permission VARCHAR(16) NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (report_id, shared_with_user_id),
    FOREIGN KEY (report_id) REFERENCES reports(id),
    FOREIGN KEY (shared_by_user_id) REFERENCES users(id),
    FOREIGN KEY (shared_with_user_id) REFERENCES users(id)
);


CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_id TEXT NOT NULL,
    session_id UUID,
    report_id UUID,
    account_id UUID,
    contact_id UUID,
    context_thread_id UUID,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    content_hash VARCHAR(128) NOT NULL,
    search_tsv TSVECTOR,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    indexed_at TIMESTAMPTZ,
    UNIQUE (source_type, source_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (report_id) REFERENCES reports(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id)
);

CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_heading VARCHAR(255),
    chunk_text TEXT NOT NULL,
    embedding_model VARCHAR(120) NOT NULL,
    token_count INTEGER,
    char_count INTEGER NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
);

