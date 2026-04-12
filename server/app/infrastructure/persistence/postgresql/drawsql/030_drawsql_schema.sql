-- CAPS DrawSQL 시각화용 스키마
-- 목적:
-- 1. DrawSQL import에 맞게 순수한 DDL만 유지한다.
-- 2. 실행용 스키마보다 컬럼 타입을 더 읽기 쉽게 드러낸다.
-- 3. FK 관계와 도메인 경계를 한눈에 보이게 한다.

CREATE TABLE workspaces (
    id VARCHAR(80) PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE users (
    id VARCHAR(80) PRIMARY KEY,
    login_id VARCHAR(120) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    job_title VARCHAR(120),
    department VARCHAR(120),
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE workspace_members (
    workspace_id VARCHAR(80) NOT NULL,
    user_id VARCHAR(80) NOT NULL,
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
    user_id VARCHAR(80) PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    password_updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE auth_sessions (
    id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(80) NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    client_type VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE accounts (
    id VARCHAR(80) PRIMARY KEY,
    workspace_id VARCHAR(80) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE contacts (
    id VARCHAR(80) PRIMARY KEY,
    workspace_id VARCHAR(80) NOT NULL,
    account_id VARCHAR(80),
    name VARCHAR(120) NOT NULL,
    email VARCHAR(320),
    job_title VARCHAR(120),
    department VARCHAR(120),
    notes TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE context_threads (
    id VARCHAR(80) PRIMARY KEY,
    workspace_id VARCHAR(80) NOT NULL,
    account_id VARCHAR(80),
    contact_id VARCHAR(80),
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    status VARCHAR(32) NOT NULL,
    created_by_user_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE sessions (
    id VARCHAR(80) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    created_by_user_id VARCHAR(80),
    account_id VARCHAR(80),
    contact_id VARCHAR(80),
    context_thread_id VARCHAR(80),
    primary_input_source VARCHAR(32) NOT NULL,
    actual_active_sources JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id)
);

CREATE TABLE session_participants (
    session_id VARCHAR(80) NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name VARCHAR(120) NOT NULL,
    normalized_participant_name VARCHAR(120) NOT NULL,
    participant_email VARCHAR(320),
    participant_job_title VARCHAR(120),
    participant_department VARCHAR(120),
    resolution_status VARCHAR(32) NOT NULL,
    contact_id VARCHAR(80),
    account_id VARCHAR(80),
    PRIMARY KEY (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE participant_followups (
    id VARCHAR(80) PRIMARY KEY,
    session_id VARCHAR(80) NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name VARCHAR(120) NOT NULL,
    resolution_status VARCHAR(32) NOT NULL,
    followup_status VARCHAR(32) NOT NULL,
    matched_contact_count INTEGER NOT NULL,
    contact_id VARCHAR(80),
    account_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    resolved_by_user_id VARCHAR(80),
    UNIQUE (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id)
);

CREATE TABLE utterances (
    id VARCHAR(80) PRIMARY KEY,
    session_id VARCHAR(80) NOT NULL,
    seq_num INTEGER NOT NULL,
    start_ms BIGINT NOT NULL,
    end_ms BIGINT NOT NULL,
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    input_source VARCHAR(32),
    stt_backend VARCHAR(80),
    latency_ms INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE overlay_events (
    id VARCHAR(80) PRIMARY KEY,
    session_id VARCHAR(80) NOT NULL,
    source_utterance_id VARCHAR(80),
    event_type VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    normalized_title VARCHAR(255),
    body TEXT,
    evidence_text TEXT,
    speaker_label VARCHAR(120),
    state VARCHAR(32) NOT NULL,
    input_source VARCHAR(32),
    insight_scope VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (source_utterance_id) REFERENCES utterances(id)
);

CREATE TABLE reports (
    id VARCHAR(80) PRIMARY KEY,
    session_id VARCHAR(80) NOT NULL,
    report_type VARCHAR(32) NOT NULL,
    version INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    insight_source VARCHAR(32) NOT NULL,
    generated_by_user_id VARCHAR(80),
    generated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (generated_by_user_id) REFERENCES users(id)
);

CREATE TABLE report_generation_jobs (
    id VARCHAR(80) PRIMARY KEY,
    session_id VARCHAR(80) NOT NULL,
    status VARCHAR(32) NOT NULL,
    recording_path TEXT,
    transcript_path TEXT,
    markdown_report_id VARCHAR(80),
    pdf_report_id VARCHAR(80),
    error_message TEXT,
    requested_by_user_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (markdown_report_id) REFERENCES reports(id),
    FOREIGN KEY (pdf_report_id) REFERENCES reports(id),
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id)
);

CREATE TABLE report_shares (
    id VARCHAR(80) PRIMARY KEY,
    report_id VARCHAR(80) NOT NULL,
    shared_by_user_id VARCHAR(80) NOT NULL,
    shared_with_user_id VARCHAR(80) NOT NULL,
    permission VARCHAR(16) NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (report_id) REFERENCES reports(id),
    FOREIGN KEY (shared_by_user_id) REFERENCES users(id),
    FOREIGN KEY (shared_with_user_id) REFERENCES users(id)
);


CREATE TABLE knowledge_documents (
    id VARCHAR(80) PRIMARY KEY,
    workspace_id VARCHAR(80) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_id TEXT NOT NULL,
    session_id VARCHAR(80),
    report_id VARCHAR(80),
    account_id VARCHAR(80),
    contact_id VARCHAR(80),
    context_thread_id VARCHAR(80),
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
    id VARCHAR(80) PRIMARY KEY,
    document_id VARCHAR(80) NOT NULL,
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

