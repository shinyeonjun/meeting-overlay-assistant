-- CAPS PostgreSQL 정본 스키마 초안
-- 현재는 설계 기준안이며 아직 런타임 코드에 직접 연결되지는 않는다.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS vector;


-- 議곗쭅 / ?뚰겕?ㅽ럹?댁뒪 / ?ъ슜??
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Seoul',
    retention_days INTEGER NOT NULL DEFAULT 365 CHECK (retention_days > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_workspaces_organization_slug UNIQUE (organization_id, slug)
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    login_id CITEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member'
        CHECK (role IN ('owner', 'admin', 'member', 'viewer', 'service')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'invited', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_role TEXT NOT NULL DEFAULT 'member'
        CHECK (workspace_role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id)
);


-- 거래처 / 상대방 / 안건 흐름

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'prospect')),
    external_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    email CITEXT,
    phone TEXT,
    job_title TEXT,
    is_internal BOOLEAN NOT NULL DEFAULT FALSE,
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    external_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS context_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    thread_type TEXT NOT NULL DEFAULT 'custom'
        CHECK (thread_type IN ('account', 'deal', 'project', 'support', 'custom')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'paused', 'closed')),
    summary TEXT,
    last_meeting_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 誘명똿 ?ㅽ뻾 ?곗씠??
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    organizer_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    primary_account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    meeting_mode TEXT NOT NULL DEFAULT 'online'
        CHECK (meeting_mode IN ('online', 'offline', 'hybrid')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'live', 'ended', 'archived')),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    primary_input_source TEXT NOT NULL
        CHECK (primary_input_source IN ('mic', 'system_audio', 'file', 'mic_and_audio')),
    actual_active_sources JSONB NOT NULL DEFAULT '[]'::JSONB,
    current_topic TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS meeting_threads (
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    context_thread_id UUID NOT NULL REFERENCES context_threads(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL DEFAULT 'primary'
        CHECK (link_type IN ('primary', 'related', 'follow_up')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (meeting_id, context_thread_id)
);

CREATE TABLE IF NOT EXISTS meeting_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    participant_kind TEXT NOT NULL
        CHECK (participant_kind IN ('internal_user', 'external_contact', 'guest')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    speaker_label TEXT,
    role TEXT NOT NULL DEFAULT 'participant'
        CHECK (role IN ('host', 'participant', 'observer')),
    attended BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_meeting_participants_target CHECK (
        (participant_kind = 'internal_user' AND user_id IS NOT NULL)
        OR (participant_kind = 'external_contact' AND contact_id IS NOT NULL)
        OR (participant_kind = 'guest' AND user_id IS NULL AND contact_id IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS utterances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    meeting_participant_id UUID REFERENCES meeting_participants(id) ON DELETE SET NULL,
    seq_num BIGINT NOT NULL,
    segment_id TEXT,
    kind TEXT NOT NULL
        CHECK (kind IN ('partial', 'live_final', 'archive_final', 'late_archive_final')),
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
    input_source TEXT
        CHECK (input_source IN ('mic', 'system_audio', 'file', 'mic_and_audio')),
    stt_backend TEXT,
    latency_ms INTEGER,
    start_ms BIGINT NOT NULL,
    end_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_utterances_meeting_seq UNIQUE (meeting_id, seq_num),
    CONSTRAINT chk_utterances_time_range CHECK (end_ms >= start_ms)
);

CREATE TABLE IF NOT EXISTS meeting_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    source_utterance_id UUID REFERENCES utterances(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL
        CHECK (event_type IN ('question', 'decision', 'action', 'risk', 'info')),
    title TEXT NOT NULL,
    normalized_title TEXT,
    body TEXT,
    evidence_text TEXT,
    speaker_label TEXT,
    state TEXT NOT NULL DEFAULT 'open'
        CHECK (state IN ('open', 'done', 'dismissed', 'deferred')),
    priority INTEGER NOT NULL DEFAULT 0 CHECK (priority >= 0 AND priority <= 100),
    assignee_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    assignee_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL,
    due_date DATE,
    topic_group TEXT,
    input_source TEXT
        CHECK (input_source IN ('mic', 'system_audio', 'file', 'mic_and_audio')),
    insight_scope TEXT NOT NULL DEFAULT 'live'
        CHECK (insight_scope IN ('live', 'post', 'carry_over')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 由ы룷??/ 怨듭쑀 / 媛먯궗

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL
        CHECK (report_type IN ('markdown', 'pdf', 'summary', 'follow_up')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'ready', 'failed')),
    storage_key TEXT,
    insight_source TEXT NOT NULL DEFAULT 'live_fallback'
        CHECK (insight_source IN ('live_fallback', 'post_meeting', 'thread_augmented')),
    generated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_reports_meeting_type_version UNIQUE (meeting_id, report_type, version)
);

CREATE TABLE IF NOT EXISTS report_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN ('markdown', 'pdf', 'transcript', 'analysis_json')),
    storage_key TEXT NOT NULL,
    content_hash TEXT,
    size_bytes BIGINT CHECK (size_bytes IS NULL OR size_bytes >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    share_type TEXT NOT NULL
        CHECK (share_type IN ('workspace_user', 'email', 'link')),
    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    target_email CITEXT,
    token_hash TEXT,
    permission TEXT NOT NULL DEFAULT 'view'
        CHECK (permission IN ('view', 'comment', 'reshare')),
    expires_at TIMESTAMPTZ,
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_report_shares_target CHECK (
        (share_type = 'workspace_user' AND target_user_id IS NOT NULL)
        OR (share_type = 'email' AND target_email IS NOT NULL)
        OR (share_type = 'link' AND token_hash IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    entity_type TEXT NOT NULL
        CHECK (entity_type IN ('meeting', 'report', 'share', 'contact', 'thread', 'account')),
    entity_id UUID NOT NULL,
    action TEXT NOT NULL
        CHECK (action IN ('create', 'update', 'read', 'share', 'revoke', 'delete', 'generate')),
    metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 寃??/ ?뚯긽

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL
        CHECK (source_type IN ('meeting', 'report', 'transcript', 'note', 'event', 'thread_summary', 'history_carry_over', 'session_summary')),
    source_id UUID NOT NULL,
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    context_thread_id UUID REFERENCES context_threads(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    body_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', COALESCE(title, '') || ' ' || COALESCE(body, ''))
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    source_ref TEXT,
    speaker_label TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    embedding VECTOR(768),
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT knowledge_chunks_start_ms_check CHECK (start_ms IS NULL OR start_ms >= 0),
    CONSTRAINT knowledge_chunks_end_ms_check CHECK (end_ms IS NULL OR end_ms >= 0),
    CONSTRAINT knowledge_chunks_timeline_check CHECK (start_ms IS NULL OR end_ms IS NULL OR end_ms >= start_ms),
    CONSTRAINT uq_knowledge_chunks_document_index UNIQUE (document_id, chunk_index)
);


-- ?몃뜳??
CREATE INDEX IF NOT EXISTS idx_accounts_workspace_name
    ON accounts(workspace_id, name);

CREATE INDEX IF NOT EXISTS idx_accounts_workspace_owner
    ON accounts(workspace_id, owner_user_id);

CREATE INDEX IF NOT EXISTS idx_contacts_account_name
    ON contacts(account_id, name);

CREATE INDEX IF NOT EXISTS idx_contacts_workspace_email
    ON contacts(workspace_id, email);

CREATE INDEX IF NOT EXISTS idx_context_threads_workspace_account_status
    ON context_threads(workspace_id, account_id, status);

CREATE INDEX IF NOT EXISTS idx_meetings_workspace_started
    ON meetings(workspace_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_meetings_workspace_account_started
    ON meetings(workspace_id, primary_account_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_meeting_participants_meeting
    ON meeting_participants(meeting_id);

CREATE INDEX IF NOT EXISTS idx_meeting_participants_contact
    ON meeting_participants(contact_id);

CREATE INDEX IF NOT EXISTS idx_meeting_participants_user
    ON meeting_participants(user_id);

CREATE INDEX IF NOT EXISTS idx_utterances_meeting_segment
    ON utterances(meeting_id, segment_id);

CREATE INDEX IF NOT EXISTS idx_utterances_meeting_kind_seq
    ON utterances(meeting_id, kind, seq_num);

CREATE INDEX IF NOT EXISTS idx_meeting_events_meeting_type_state
    ON meeting_events(meeting_id, event_type, state);

CREATE INDEX IF NOT EXISTS idx_meeting_events_meeting_created
    ON meeting_events(meeting_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_meeting_events_meeting_normalized
    ON meeting_events(meeting_id, event_type, normalized_title, state);

CREATE INDEX IF NOT EXISTS idx_reports_meeting_generated
    ON reports(meeting_id, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_report_artifacts_report
    ON report_artifacts(report_id, artifact_type);

CREATE INDEX IF NOT EXISTS idx_report_shares_report
    ON report_shares(report_id);

CREATE INDEX IF NOT EXISTS idx_report_shares_target_user
    ON report_shares(target_user_id);

CREATE INDEX IF NOT EXISTS idx_report_shares_token
    ON report_shares(token_hash);

CREATE INDEX IF NOT EXISTS idx_audit_logs_workspace_entity
    ON audit_logs(workspace_id, entity_type, entity_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_workspace_actor
    ON audit_logs(workspace_id, actor_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_workspace_source
    ON knowledge_documents(workspace_id, source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_account
    ON knowledge_documents(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_thread
    ON knowledge_documents(context_thread_id, created_at DESC);

CREATE INDEX IF NOT EXISTS gin_knowledge_documents_body_tsv
    ON knowledge_documents USING GIN (body_tsv);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge_chunks(document_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_ref
    ON knowledge_chunks(source_ref);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_timeline
    ON knowledge_chunks(document_id, start_ms, end_ms);

CREATE INDEX IF NOT EXISTS ivfflat_knowledge_chunks_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

