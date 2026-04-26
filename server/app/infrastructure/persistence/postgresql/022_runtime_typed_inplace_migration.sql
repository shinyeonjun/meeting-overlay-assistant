-- CAPS PostgreSQL 2차 타입 개선 in-place migration
-- 목표:
-- 1. 현재 runtime-compatible 스키마(020)로 운영 중인 DB를 실제 타입 개선 스키마로 옮긴다.
-- 2. 문자열 prefix 기반 ID를 UUID로 안정적으로 치환한다.
-- 3. 문자열 시간 컬럼을 TIMESTAMPTZ로 변환한다.
-- 4. 현재 DB를 바로 ALTER 하기보다 shadow table 재적재 방식으로 안전하게 교체한다.

BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'workspaces'
          AND column_name = 'id'
          AND udt_name = 'uuid'
    ) THEN
        RAISE EXCEPTION '이미 UUID 기반 스키마로 보입니다. 022 migration은 020 runtime DB 기준으로만 실행해야 합니다.';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION caps_legacy_text_to_uuid(value TEXT)
RETURNS UUID
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
    hex TEXT;
BEGIN
    IF value IS NULL OR NULLIF(BTRIM(value), '') IS NULL THEN
        RETURN NULL;
    END IF;

    normalized := BTRIM(value);

    IF pg_input_is_valid(normalized, 'uuid') THEN
        RETURN normalized::uuid;
    END IF;

    IF normalized ~* '^[0-9a-f]{32}$' THEN
        hex := LOWER(normalized);
    ELSIF normalized ~* '([0-9a-f]{32})$' THEN
        hex := LOWER(SUBSTRING(normalized FROM '([0-9a-f]{32})$'));
    ELSE
        hex := MD5(normalized);
    END IF;

    RETURN (
        SUBSTRING(hex FROM 1 FOR 8) || '-' ||
        SUBSTRING(hex FROM 9 FOR 4) || '-' ||
        SUBSTRING(hex FROM 13 FOR 4) || '-' ||
        SUBSTRING(hex FROM 17 FOR 4) || '-' ||
        SUBSTRING(hex FROM 21 FOR 12)
    )::uuid;
END;
$$;

CREATE OR REPLACE FUNCTION caps_legacy_text_to_timestamptz(value TEXT)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized TEXT;
BEGIN
    IF value IS NULL OR NULLIF(BTRIM(value), '') IS NULL THEN
        RETURN NULL;
    END IF;

    normalized := BTRIM(value);
    RETURN normalized::timestamptz;
END;
$$;

CREATE OR REPLACE FUNCTION caps_assert_timestamptz_convertible(p_table TEXT, p_column TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count BIGINT;
BEGIN
    EXECUTE FORMAT(
        'SELECT COUNT(*) FROM %I WHERE %I IS NOT NULL AND NULLIF(BTRIM(%I), '''') IS NOT NULL AND NOT pg_input_is_valid(%I, ''timestamp with time zone'')',
        p_table,
        p_column,
        p_column,
        p_column
    )
    INTO invalid_count;

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'TIMESTAMPTZ 변환 불가 데이터가 있습니다: %.% (%건)', p_table, p_column, invalid_count;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION caps_assert_uuid_mapping_unique(p_table TEXT, p_column TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    collision_count BIGINT;
BEGIN
    EXECUTE FORMAT(
        'SELECT COUNT(*) FROM (
            SELECT caps_legacy_text_to_uuid(%1$I) AS mapped_uuid
            FROM %2$I
            WHERE %1$I IS NOT NULL AND NULLIF(BTRIM(%1$I), '''') IS NOT NULL
            GROUP BY 1
            HAVING COUNT(*) > 1
        ) AS collisions',
        p_column,
        p_table
    )
    INTO collision_count;

    IF collision_count > 0 THEN
        RAISE EXCEPTION 'UUID 매핑 충돌이 있습니다: %.% (%건)', p_table, p_column, collision_count;
    END IF;
END;
$$;

SELECT caps_assert_uuid_mapping_unique('workspaces', 'id');
SELECT caps_assert_uuid_mapping_unique('users', 'id');
SELECT caps_assert_uuid_mapping_unique('accounts', 'id');
SELECT caps_assert_uuid_mapping_unique('contacts', 'id');
SELECT caps_assert_uuid_mapping_unique('context_threads', 'id');
SELECT caps_assert_uuid_mapping_unique('sessions', 'id');
SELECT caps_assert_uuid_mapping_unique('participant_followups', 'id');
SELECT caps_assert_uuid_mapping_unique('reports', 'id');
SELECT caps_assert_uuid_mapping_unique('session_post_processing_jobs', 'id');
SELECT caps_assert_uuid_mapping_unique('note_correction_jobs', 'id');
SELECT caps_assert_uuid_mapping_unique('report_generation_jobs', 'id');
SELECT caps_assert_uuid_mapping_unique('report_shares', 'id');
SELECT caps_assert_uuid_mapping_unique('utterances', 'id');
SELECT caps_assert_uuid_mapping_unique('overlay_events', 'id');
SELECT caps_assert_uuid_mapping_unique('knowledge_documents', 'id');
SELECT caps_assert_uuid_mapping_unique('knowledge_chunks', 'id');

SELECT caps_assert_timestamptz_convertible('workspaces', 'created_at');
SELECT caps_assert_timestamptz_convertible('workspaces', 'updated_at');
SELECT caps_assert_timestamptz_convertible('users', 'created_at');
SELECT caps_assert_timestamptz_convertible('users', 'updated_at');
SELECT caps_assert_timestamptz_convertible('workspace_members', 'joined_at');
SELECT caps_assert_timestamptz_convertible('workspace_members', 'created_at');
SELECT caps_assert_timestamptz_convertible('workspace_members', 'updated_at');
SELECT caps_assert_timestamptz_convertible('auth_password_credentials', 'password_updated_at');
SELECT caps_assert_timestamptz_convertible('auth_sessions', 'created_at');
SELECT caps_assert_timestamptz_convertible('auth_sessions', 'expires_at');
SELECT caps_assert_timestamptz_convertible('auth_sessions', 'revoked_at');
SELECT caps_assert_timestamptz_convertible('auth_sessions', 'last_seen_at');
SELECT caps_assert_timestamptz_convertible('accounts', 'created_at');
SELECT caps_assert_timestamptz_convertible('accounts', 'updated_at');
SELECT caps_assert_timestamptz_convertible('contacts', 'created_at');
SELECT caps_assert_timestamptz_convertible('contacts', 'updated_at');
SELECT caps_assert_timestamptz_convertible('context_threads', 'created_at');
SELECT caps_assert_timestamptz_convertible('context_threads', 'updated_at');
SELECT caps_assert_timestamptz_convertible('sessions', 'started_at');
SELECT caps_assert_timestamptz_convertible('sessions', 'ended_at');
SELECT caps_assert_timestamptz_convertible('sessions', 'recovery_detected_at');
SELECT caps_assert_timestamptz_convertible('sessions', 'post_processing_requested_at');
SELECT caps_assert_timestamptz_convertible('sessions', 'post_processing_started_at');
SELECT caps_assert_timestamptz_convertible('sessions', 'post_processing_completed_at');
SELECT caps_assert_timestamptz_convertible('participant_followups', 'created_at');
SELECT caps_assert_timestamptz_convertible('participant_followups', 'updated_at');
SELECT caps_assert_timestamptz_convertible('participant_followups', 'resolved_at');
SELECT caps_assert_timestamptz_convertible('reports', 'generated_at');
SELECT caps_assert_timestamptz_convertible('session_post_processing_jobs', 'lease_expires_at');
SELECT caps_assert_timestamptz_convertible('session_post_processing_jobs', 'created_at');
SELECT caps_assert_timestamptz_convertible('session_post_processing_jobs', 'started_at');
SELECT caps_assert_timestamptz_convertible('session_post_processing_jobs', 'completed_at');
SELECT caps_assert_timestamptz_convertible('note_correction_jobs', 'lease_expires_at');
SELECT caps_assert_timestamptz_convertible('note_correction_jobs', 'created_at');
SELECT caps_assert_timestamptz_convertible('note_correction_jobs', 'started_at');
SELECT caps_assert_timestamptz_convertible('note_correction_jobs', 'completed_at');
SELECT caps_assert_timestamptz_convertible('report_generation_jobs', 'lease_expires_at');
SELECT caps_assert_timestamptz_convertible('report_generation_jobs', 'created_at');
SELECT caps_assert_timestamptz_convertible('report_generation_jobs', 'started_at');
SELECT caps_assert_timestamptz_convertible('report_generation_jobs', 'completed_at');
SELECT caps_assert_timestamptz_convertible('report_shares', 'created_at');

-- shadow tables
CREATE TABLE next_workspaces (
    id UUID PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE next_users (
    id UUID PRIMARY KEY,
    login_id CITEXT NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    job_title VARCHAR(120),
    department VARCHAR(120),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE next_workspace_members (
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    workspace_role VARCHAR(32) NOT NULL DEFAULT 'member',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    joined_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES next_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES next_users(id) ON DELETE CASCADE
);

CREATE TABLE next_auth_password_credentials (
    user_id UUID PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    password_updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (user_id) REFERENCES next_users(id) ON DELETE CASCADE
);

CREATE TABLE next_auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    client_type VARCHAR(32) NOT NULL DEFAULT 'desktop',
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    FOREIGN KEY (user_id) REFERENCES next_users(id) ON DELETE CASCADE
);

CREATE TABLE next_accounts (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_by_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES next_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_contacts (
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
    FOREIGN KEY (workspace_id) REFERENCES next_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES next_accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_context_threads (
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
    FOREIGN KEY (workspace_id) REFERENCES next_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES next_accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES next_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_sessions (
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
    FOREIGN KEY (created_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES next_accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES next_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (context_thread_id) REFERENCES next_context_threads(id) ON DELETE SET NULL
);

CREATE TABLE next_session_participants (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES next_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES next_accounts(id) ON DELETE SET NULL
);

CREATE TABLE next_participant_followups (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES next_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES next_accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_reports (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_session_post_processing_jobs (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_note_correction_jobs (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_report_generation_jobs (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (markdown_report_id) REFERENCES next_reports(id) ON DELETE SET NULL,
    FOREIGN KEY (pdf_report_id) REFERENCES next_reports(id) ON DELETE SET NULL,
    FOREIGN KEY (requested_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL
);

CREATE TABLE next_report_shares (
    id UUID PRIMARY KEY,
    report_id UUID NOT NULL,
    shared_by_user_id UUID,
    shared_with_user_id UUID NOT NULL,
    permission VARCHAR(16) NOT NULL DEFAULT 'view',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (report_id) REFERENCES next_reports(id) ON DELETE CASCADE,
    FOREIGN KEY (shared_by_user_id) REFERENCES next_users(id) ON DELETE SET NULL,
    FOREIGN KEY (shared_with_user_id) REFERENCES next_users(id) ON DELETE CASCADE
);

CREATE TABLE next_utterances (
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
    UNIQUE (session_id, seq_num),
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (processing_job_id) REFERENCES next_session_post_processing_jobs(id) ON DELETE SET NULL
);

CREATE TABLE next_overlay_events (
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
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (source_utterance_id) REFERENCES next_utterances(id) ON DELETE SET NULL,
    FOREIGN KEY (processing_job_id) REFERENCES next_session_post_processing_jobs(id) ON DELETE SET NULL
);

CREATE TABLE next_knowledge_documents (
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
    FOREIGN KEY (workspace_id) REFERENCES next_workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES next_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES next_reports(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES next_accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES next_contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (context_thread_id) REFERENCES next_context_threads(id) ON DELETE SET NULL
);

CREATE TABLE next_knowledge_chunks (
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
    FOREIGN KEY (document_id) REFERENCES next_knowledge_documents(id) ON DELETE CASCADE
);

-- data copy
INSERT INTO next_workspaces (id, slug, name, status, created_at, updated_at)
SELECT
    caps_legacy_text_to_uuid(id),
    slug,
    name,
    COALESCE(NULLIF(BTRIM(status), ''), 'active'),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at)
FROM workspaces;

INSERT INTO next_users (id, login_id, display_name, job_title, department, status, created_at, updated_at)
SELECT
    caps_legacy_text_to_uuid(id),
    login_id,
    display_name,
    job_title,
    department,
    COALESCE(NULLIF(BTRIM(status), ''), 'active'),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at)
FROM users;

INSERT INTO next_workspace_members (workspace_id, user_id, workspace_role, status, joined_at, created_at, updated_at)
SELECT
    caps_legacy_text_to_uuid(workspace_id),
    caps_legacy_text_to_uuid(user_id),
    COALESCE(NULLIF(BTRIM(workspace_role), ''), 'member'),
    COALESCE(NULLIF(BTRIM(status), ''), 'active'),
    caps_legacy_text_to_timestamptz(joined_at),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at)
FROM workspace_members;

INSERT INTO next_auth_password_credentials (user_id, password_hash, password_updated_at)
SELECT
    caps_legacy_text_to_uuid(user_id),
    password_hash,
    caps_legacy_text_to_timestamptz(password_updated_at)
FROM auth_password_credentials;

INSERT INTO next_auth_sessions (id, user_id, token_hash, client_type, created_at, expires_at, revoked_at, last_seen_at)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(user_id),
    token_hash,
    COALESCE(NULLIF(BTRIM(client_type), ''), 'desktop'),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(expires_at),
    caps_legacy_text_to_timestamptz(revoked_at),
    caps_legacy_text_to_timestamptz(last_seen_at)
FROM auth_sessions;

INSERT INTO next_accounts (id, workspace_id, name, description, status, created_by_user_id, created_at, updated_at)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(workspace_id),
    name,
    description,
    COALESCE(NULLIF(BTRIM(status), ''), 'active'),
    caps_legacy_text_to_uuid(created_by_user_id),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at)
FROM accounts;

INSERT INTO next_contacts (id, workspace_id, account_id, name, email, job_title, department, notes, status, created_by_user_id, created_at, updated_at)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(workspace_id),
    caps_legacy_text_to_uuid(account_id),
    name,
    email,
    job_title,
    department,
    notes,
    COALESCE(NULLIF(BTRIM(status), ''), 'active'),
    caps_legacy_text_to_uuid(created_by_user_id),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at)
FROM contacts;

INSERT INTO next_context_threads (id, workspace_id, account_id, contact_id, title, summary, status, created_by_user_id, created_at, updated_at)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(workspace_id),
    caps_legacy_text_to_uuid(account_id),
    caps_legacy_text_to_uuid(contact_id),
    title,
    summary,
    COALESCE(NULLIF(BTRIM(status), ''), 'active'),
    caps_legacy_text_to_uuid(created_by_user_id),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at)
FROM context_threads;

INSERT INTO next_sessions (
    id,
    title,
    mode,
    created_by_user_id,
    account_id,
    contact_id,
    context_thread_id,
    primary_input_source,
    actual_active_sources,
    started_at,
    ended_at,
    recovery_required,
    recovery_reason,
    recovery_detected_at,
    recording_artifact_id,
    post_processing_status,
    post_processing_error_message,
    post_processing_requested_at,
    post_processing_started_at,
    post_processing_completed_at,
    canonical_transcript_version,
    canonical_events_version,
    status
)
SELECT
    caps_legacy_text_to_uuid(id),
    title,
    mode,
    caps_legacy_text_to_uuid(created_by_user_id),
    caps_legacy_text_to_uuid(account_id),
    caps_legacy_text_to_uuid(contact_id),
    caps_legacy_text_to_uuid(context_thread_id),
    COALESCE(NULLIF(BTRIM(primary_input_source), ''), 'system_audio'),
    COALESCE(actual_active_sources, '[]'::jsonb),
    caps_legacy_text_to_timestamptz(started_at),
    caps_legacy_text_to_timestamptz(ended_at),
    COALESCE(recovery_required, FALSE),
    recovery_reason,
    caps_legacy_text_to_timestamptz(recovery_detected_at),
    recording_artifact_id,
    COALESCE(NULLIF(BTRIM(post_processing_status), ''), 'not_started'),
    post_processing_error_message,
    caps_legacy_text_to_timestamptz(post_processing_requested_at),
    caps_legacy_text_to_timestamptz(post_processing_started_at),
    caps_legacy_text_to_timestamptz(post_processing_completed_at),
    COALESCE(canonical_transcript_version, 0),
    COALESCE(canonical_events_version, 0),
    status
FROM sessions;

INSERT INTO next_session_participants (
    session_id,
    participant_order,
    participant_name,
    normalized_participant_name,
    participant_email,
    participant_job_title,
    participant_department,
    resolution_status,
    contact_id,
    account_id
)
SELECT
    caps_legacy_text_to_uuid(session_id),
    participant_order,
    participant_name,
    normalized_participant_name,
    participant_email,
    participant_job_title,
    participant_department,
    COALESCE(NULLIF(BTRIM(resolution_status), ''), 'unmatched'),
    caps_legacy_text_to_uuid(contact_id),
    caps_legacy_text_to_uuid(account_id)
FROM session_participants;

INSERT INTO next_participant_followups (
    id,
    session_id,
    participant_order,
    participant_name,
    resolution_status,
    followup_status,
    matched_contact_count,
    contact_id,
    account_id,
    created_at,
    updated_at,
    resolved_at,
    resolved_by_user_id
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    participant_order,
    participant_name,
    resolution_status,
    COALESCE(NULLIF(BTRIM(followup_status), ''), 'pending'),
    COALESCE(matched_contact_count, 0),
    caps_legacy_text_to_uuid(contact_id),
    caps_legacy_text_to_uuid(account_id),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(updated_at),
    caps_legacy_text_to_timestamptz(resolved_at),
    caps_legacy_text_to_uuid(resolved_by_user_id)
FROM participant_followups;

INSERT INTO next_reports (
    id,
    session_id,
    report_type,
    version,
    file_artifact_id,
    file_path,
    insight_source,
    generated_by_user_id,
    generated_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    report_type,
    version,
    file_artifact_id,
    file_path,
    COALESCE(NULLIF(BTRIM(insight_source), ''), 'live_fallback'),
    caps_legacy_text_to_uuid(generated_by_user_id),
    caps_legacy_text_to_timestamptz(generated_at)
FROM reports;

INSERT INTO next_session_post_processing_jobs (
    id,
    session_id,
    status,
    recording_artifact_id,
    recording_path,
    error_message,
    requested_by_user_id,
    claimed_by_worker_id,
    lease_expires_at,
    attempt_count,
    created_at,
    started_at,
    completed_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    status,
    recording_artifact_id,
    recording_path,
    error_message,
    caps_legacy_text_to_uuid(requested_by_user_id),
    claimed_by_worker_id,
    caps_legacy_text_to_timestamptz(lease_expires_at),
    COALESCE(attempt_count, 0),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(started_at),
    caps_legacy_text_to_timestamptz(completed_at)
FROM session_post_processing_jobs;

INSERT INTO next_note_correction_jobs (
    id,
    session_id,
    source_version,
    status,
    error_message,
    requested_by_user_id,
    claimed_by_worker_id,
    lease_expires_at,
    attempt_count,
    created_at,
    started_at,
    completed_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    COALESCE(source_version, 0),
    status,
    error_message,
    caps_legacy_text_to_uuid(requested_by_user_id),
    claimed_by_worker_id,
    caps_legacy_text_to_timestamptz(lease_expires_at),
    COALESCE(attempt_count, 0),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(started_at),
    caps_legacy_text_to_timestamptz(completed_at)
FROM note_correction_jobs;

INSERT INTO next_report_generation_jobs (
    id,
    session_id,
    status,
    recording_artifact_id,
    recording_path,
    transcript_path,
    markdown_report_id,
    pdf_report_id,
    error_message,
    requested_by_user_id,
    claimed_by_worker_id,
    lease_expires_at,
    attempt_count,
    created_at,
    started_at,
    completed_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    status,
    recording_artifact_id,
    recording_path,
    transcript_path,
    caps_legacy_text_to_uuid(markdown_report_id),
    caps_legacy_text_to_uuid(pdf_report_id),
    error_message,
    caps_legacy_text_to_uuid(requested_by_user_id),
    claimed_by_worker_id,
    caps_legacy_text_to_timestamptz(lease_expires_at),
    COALESCE(attempt_count, 0),
    caps_legacy_text_to_timestamptz(created_at),
    caps_legacy_text_to_timestamptz(started_at),
    caps_legacy_text_to_timestamptz(completed_at)
FROM report_generation_jobs;

INSERT INTO next_report_shares (
    id,
    report_id,
    shared_by_user_id,
    shared_with_user_id,
    permission,
    note,
    created_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(report_id),
    caps_legacy_text_to_uuid(shared_by_user_id),
    caps_legacy_text_to_uuid(shared_with_user_id),
    COALESCE(NULLIF(BTRIM(permission), ''), 'view'),
    note,
    caps_legacy_text_to_timestamptz(created_at)
FROM report_shares;

INSERT INTO next_utterances (
    id,
    session_id,
    seq_num,
    start_ms,
    end_ms,
    text,
    confidence,
    input_source,
    stt_backend,
    latency_ms,
    speaker_label,
    transcript_source,
    processing_job_id
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    seq_num,
    start_ms,
    end_ms,
    text,
    COALESCE(confidence, 0.0),
    input_source,
    stt_backend,
    latency_ms,
    speaker_label,
    COALESCE(NULLIF(BTRIM(transcript_source), ''), 'live'),
    caps_legacy_text_to_uuid(processing_job_id)
FROM utterances;

INSERT INTO next_overlay_events (
    id,
    session_id,
    source_utterance_id,
    event_type,
    title,
    normalized_title,
    body,
    evidence_text,
    speaker_label,
    state,
    input_source,
    insight_scope,
    event_source,
    processing_job_id,
    created_at,
    updated_at,
    finalized_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(session_id),
    caps_legacy_text_to_uuid(source_utterance_id),
    event_type,
    title,
    normalized_title,
    body,
    evidence_text,
    speaker_label,
    state,
    input_source,
    COALESCE(NULLIF(BTRIM(insight_scope), ''), 'live'),
    COALESCE(NULLIF(BTRIM(event_source), ''), 'live'),
    caps_legacy_text_to_uuid(processing_job_id),
    created_at,
    updated_at,
    finalized_at
FROM overlay_events;

INSERT INTO next_knowledge_documents (
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
    created_at,
    updated_at,
    indexed_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(workspace_id),
    source_type,
    source_id,
    caps_legacy_text_to_uuid(session_id),
    caps_legacy_text_to_uuid(report_id),
    caps_legacy_text_to_uuid(account_id),
    caps_legacy_text_to_uuid(contact_id),
    caps_legacy_text_to_uuid(context_thread_id),
    title,
    body,
    content_hash,
    created_at,
    updated_at,
    indexed_at
FROM knowledge_documents;

INSERT INTO next_knowledge_chunks (
    id,
    document_id,
    chunk_index,
    chunk_heading,
    chunk_text,
    embedding_model,
    token_count,
    char_count,
    embedding,
    created_at
)
SELECT
    caps_legacy_text_to_uuid(id),
    caps_legacy_text_to_uuid(document_id),
    chunk_index,
    chunk_heading,
    chunk_text,
    embedding_model,
    COALESCE(token_count, 0),
    COALESCE(char_count, 0),
    embedding,
    created_at
FROM knowledge_chunks;

DROP TABLE IF EXISTS knowledge_chunks CASCADE;
DROP TABLE IF EXISTS knowledge_documents CASCADE;
DROP TABLE IF EXISTS report_shares CASCADE;
DROP TABLE IF EXISTS report_generation_jobs CASCADE;
DROP TABLE IF EXISTS note_correction_jobs CASCADE;
DROP TABLE IF EXISTS session_post_processing_jobs CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS overlay_events CASCADE;
DROP TABLE IF EXISTS utterances CASCADE;
DROP TABLE IF EXISTS participant_followups CASCADE;
DROP TABLE IF EXISTS session_participants CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS context_threads CASCADE;
DROP TABLE IF EXISTS contacts CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS auth_sessions CASCADE;
DROP TABLE IF EXISTS auth_password_credentials CASCADE;
DROP TABLE IF EXISTS workspace_members CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;

ALTER TABLE next_workspaces RENAME TO workspaces;
ALTER TABLE next_users RENAME TO users;
ALTER TABLE next_workspace_members RENAME TO workspace_members;
ALTER TABLE next_auth_password_credentials RENAME TO auth_password_credentials;
ALTER TABLE next_auth_sessions RENAME TO auth_sessions;
ALTER TABLE next_accounts RENAME TO accounts;
ALTER TABLE next_contacts RENAME TO contacts;
ALTER TABLE next_context_threads RENAME TO context_threads;
ALTER TABLE next_sessions RENAME TO sessions;
ALTER TABLE next_session_participants RENAME TO session_participants;
ALTER TABLE next_participant_followups RENAME TO participant_followups;
ALTER TABLE next_reports RENAME TO reports;
ALTER TABLE next_session_post_processing_jobs RENAME TO session_post_processing_jobs;
ALTER TABLE next_note_correction_jobs RENAME TO note_correction_jobs;
ALTER TABLE next_report_generation_jobs RENAME TO report_generation_jobs;
ALTER TABLE next_report_shares RENAME TO report_shares;
ALTER TABLE next_utterances RENAME TO utterances;
ALTER TABLE next_overlay_events RENAME TO overlay_events;
ALTER TABLE next_knowledge_documents RENAME TO knowledge_documents;
ALTER TABLE next_knowledge_chunks RENAME TO knowledge_chunks;

CREATE UNIQUE INDEX uq_report_shares_report_recipient
    ON report_shares(report_id, shared_with_user_id);

CREATE INDEX idx_utterances_session_seq
    ON utterances(session_id, seq_num);

CREATE INDEX idx_overlay_events_session_type
    ON overlay_events(session_id, event_type, state);

CREATE INDEX idx_overlay_events_session_created
    ON overlay_events(session_id, created_at);

CREATE INDEX idx_overlay_events_source_utterance
    ON overlay_events(session_id, source_utterance_id, created_at);

CREATE INDEX idx_reports_session_generated
    ON reports(session_id, generated_at);

CREATE INDEX idx_session_post_processing_jobs_session_created
    ON session_post_processing_jobs(session_id, created_at);

CREATE INDEX idx_session_post_processing_jobs_status_created
    ON session_post_processing_jobs(status, created_at);

CREATE INDEX idx_session_post_processing_jobs_claimable
    ON session_post_processing_jobs(status, lease_expires_at, created_at);

CREATE INDEX idx_note_correction_jobs_session_created
    ON note_correction_jobs(session_id, created_at);

CREATE INDEX idx_note_correction_jobs_status_created
    ON note_correction_jobs(status, created_at);

CREATE INDEX idx_note_correction_jobs_claimable
    ON note_correction_jobs(status, lease_expires_at, created_at);

CREATE INDEX idx_report_generation_jobs_session_created
    ON report_generation_jobs(session_id, created_at);

CREATE INDEX idx_report_generation_jobs_status_created
    ON report_generation_jobs(status, created_at);

CREATE INDEX idx_report_generation_jobs_claimable
    ON report_generation_jobs(status, lease_expires_at, created_at);

CREATE INDEX idx_report_shares_report_created
    ON report_shares(report_id, created_at);

CREATE INDEX idx_report_shares_recipient_created
    ON report_shares(shared_with_user_id, created_at);

CREATE INDEX idx_sessions_status_started
    ON sessions(status, started_at);

CREATE INDEX idx_sessions_created_by_user
    ON sessions(created_by_user_id, started_at);

CREATE INDEX idx_sessions_account_started
    ON sessions(account_id, started_at);

CREATE INDEX idx_sessions_contact_started
    ON sessions(contact_id, started_at);

CREATE INDEX idx_sessions_context_thread_started
    ON sessions(context_thread_id, started_at);

CREATE INDEX idx_sessions_post_processing_status_started
    ON sessions(post_processing_status, started_at);

CREATE INDEX idx_session_participants_session_order
    ON session_participants(session_id, participant_order);

CREATE INDEX idx_session_participants_contact
    ON session_participants(contact_id, session_id);

CREATE INDEX idx_session_participants_account_normalized_name
    ON session_participants(account_id, normalized_participant_name);

CREATE INDEX idx_session_participants_resolution_status
    ON session_participants(resolution_status, session_id);

CREATE INDEX idx_participant_followups_session_status
    ON participant_followups(session_id, followup_status, participant_order);

CREATE INDEX idx_participant_followups_status_created
    ON participant_followups(followup_status, created_at);

CREATE INDEX idx_participant_followups_contact_status
    ON participant_followups(contact_id, followup_status);

CREATE INDEX idx_users_login_id
    ON users(login_id);

CREATE INDEX idx_workspace_members_user_status
    ON workspace_members(user_id, status);

CREATE INDEX idx_workspace_members_role
    ON workspace_members(workspace_id, workspace_role, status);

CREATE INDEX idx_accounts_workspace_name
    ON accounts(workspace_id, name);

CREATE INDEX idx_contacts_workspace_account_name
    ON contacts(workspace_id, account_id, name);

CREATE INDEX idx_context_threads_workspace_updated
    ON context_threads(workspace_id, updated_at);

CREATE INDEX idx_auth_sessions_user
    ON auth_sessions(user_id, created_at);

CREATE INDEX idx_auth_sessions_expires
    ON auth_sessions(expires_at);

CREATE INDEX idx_knowledge_documents_workspace_source
    ON knowledge_documents(workspace_id, source_type, source_id);

CREATE INDEX idx_knowledge_documents_session_updated
    ON knowledge_documents(session_id, updated_at DESC);

CREATE INDEX idx_knowledge_documents_report_id
    ON knowledge_documents(report_id);

CREATE INDEX idx_knowledge_documents_account_created
    ON knowledge_documents(account_id, updated_at DESC);

CREATE INDEX idx_knowledge_documents_contact_created
    ON knowledge_documents(contact_id, updated_at DESC);

CREATE INDEX idx_knowledge_documents_thread_created
    ON knowledge_documents(context_thread_id, updated_at DESC);

CREATE INDEX gin_knowledge_documents_search_tsv
    ON knowledge_documents USING GIN (search_tsv);

CREATE INDEX idx_knowledge_chunks_document
    ON knowledge_chunks(document_id, chunk_index);

CREATE INDEX hnsw_knowledge_chunks_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

DROP FUNCTION IF EXISTS caps_assert_timestamptz_convertible(TEXT, TEXT);
DROP FUNCTION IF EXISTS caps_assert_uuid_mapping_unique(TEXT, TEXT);
DROP FUNCTION IF EXISTS caps_legacy_text_to_timestamptz(TEXT);
DROP FUNCTION IF EXISTS caps_legacy_text_to_uuid(TEXT);

COMMIT;
