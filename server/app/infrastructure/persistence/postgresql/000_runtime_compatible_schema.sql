-- CAPS PostgreSQL 1李??명솚 ?ㅽ궎留?珥덉븞
-- 紐⑺몴:
-- 1. 현재 runtime 테이블 이름과 계약을 그대로 유지한다.
-- 2. 泥?PostgreSQL 而룹삤踰꾨뒗 repository swap ?섏??쇰줈 ?앸궦??
-- 3. pgvector / knowledge_* / 援ъ“ 媛쒕챸? 2李??밴꺽?쇰줈 誘몃，??

CREATE EXTENSION IF NOT EXISTS citext;

-- ?뚰겕?ㅽ럹?댁뒪 / ?ъ슜??/ ?몄쬆
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    login_id CITEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    job_title TEXT,
    department TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS login_id CITEXT;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
          AND column_name = 'email'
    ) THEN
        EXECUTE '
            UPDATE users
            SET login_id = COALESCE(login_id, NULLIF(BTRIM(email::text), ''''))
        ';
    END IF;
END $$;

ALTER TABLE users
    ALTER COLUMN login_id SET NOT NULL;

ALTER TABLE users
    DROP COLUMN IF EXISTS email;

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    workspace_role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'active',
    joined_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auth_password_credentials (
    user_id TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    password_updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    client_type TEXT NOT NULL DEFAULT 'desktop',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    last_seen_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 留λ씫
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT,
    name TEXT NOT NULL,
    email CITEXT,
    job_title TEXT,
    department TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS context_threads (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT,
    contact_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ?몄뀡 / 李몄뿬??
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    mode TEXT NOT NULL,
    created_by_user_id TEXT,
    account_id TEXT,
    contact_id TEXT,
    context_thread_id TEXT,
    primary_input_source TEXT NOT NULL,
    actual_active_sources JSONB NOT NULL DEFAULT '[]'::JSONB,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id) ON DELETE SET NULL
);

ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS primary_input_source TEXT,
    ADD COLUMN IF NOT EXISTS actual_active_sources JSONB;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'sessions'
          AND column_name = 'source'
    ) THEN
        EXECUTE '
            UPDATE sessions
            SET primary_input_source = COALESCE(primary_input_source, NULLIF(BTRIM(source::text), ''''))
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'sessions'
          AND column_name = 'actual_active_sources'
          AND data_type <> 'jsonb'
    ) THEN
        EXECUTE '
            ALTER TABLE sessions
            ALTER COLUMN actual_active_sources TYPE JSONB
            USING CASE
                WHEN actual_active_sources IS NULL THEN ''[]''::jsonb
                WHEN NULLIF(BTRIM(actual_active_sources::text), '''') IS NULL THEN ''[]''::jsonb
                ELSE actual_active_sources::jsonb
            END
        ';
    END IF;
END $$;

UPDATE sessions
SET primary_input_source = COALESCE(primary_input_source, 'system_audio')
WHERE primary_input_source IS NULL;

UPDATE sessions
SET actual_active_sources = COALESCE(actual_active_sources, '[]'::jsonb)
WHERE actual_active_sources IS NULL;

ALTER TABLE sessions
    ALTER COLUMN primary_input_source SET NOT NULL,
    ALTER COLUMN actual_active_sources SET DEFAULT '[]'::jsonb,
    ALTER COLUMN actual_active_sources SET NOT NULL;

ALTER TABLE sessions
    DROP COLUMN IF EXISTS source;

CREATE TABLE IF NOT EXISTS session_participants (
    session_id TEXT NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name TEXT NOT NULL,
    normalized_participant_name TEXT NOT NULL,
    participant_email CITEXT,
    participant_job_title TEXT,
    participant_department TEXT,
    resolution_status TEXT NOT NULL DEFAULT 'unmatched',
    contact_id TEXT,
    account_id TEXT,
    PRIMARY KEY (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS participant_followups (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    participant_order INTEGER NOT NULL,
    participant_name TEXT NOT NULL,
    resolution_status TEXT NOT NULL,
    followup_status TEXT NOT NULL DEFAULT 'pending',
    matched_contact_count INTEGER NOT NULL DEFAULT 0,
    contact_id TEXT,
    account_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by_user_id TEXT,
    UNIQUE (session_id, participant_order),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- STT / ?붾㈃ / ?대깽??CREATE TABLE IF NOT EXISTS utterances (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    seq_num INTEGER NOT NULL,
    start_ms BIGINT NOT NULL,
    end_ms BIGINT NOT NULL,
    text TEXT NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 0.0,
    input_source TEXT,
    stt_backend TEXT,
    latency_ms INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS overlay_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_utterance_id TEXT,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT,
    body TEXT,
    evidence_text TEXT,
    speaker_label TEXT,
    state TEXT NOT NULL,
    input_source TEXT,
    insight_scope TEXT NOT NULL DEFAULT 'live',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (source_utterance_id) REFERENCES utterances(id) ON DELETE SET NULL
);

ALTER TABLE overlay_events
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'overlay_events'
          AND column_name = 'created_at_ms'
    ) THEN
        EXECUTE '
            UPDATE overlay_events
            SET created_at = COALESCE(created_at, to_timestamp(created_at_ms / 1000.0))
        ';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'overlay_events'
          AND column_name = 'updated_at_ms'
    ) THEN
        EXECUTE '
            UPDATE overlay_events
            SET updated_at = COALESCE(updated_at, to_timestamp(updated_at_ms / 1000.0))
        ';
    END IF;
END $$;

ALTER TABLE overlay_events
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET NOT NULL;

DROP INDEX IF EXISTS idx_overlay_events_session_created;
DROP INDEX IF EXISTS idx_overlay_events_source_utterance;

ALTER TABLE overlay_events
    DROP COLUMN IF EXISTS created_at_ms,
    DROP COLUMN IF EXISTS updated_at_ms;

-- 由ы룷??
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    report_type TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    file_artifact_id TEXT,
    file_path TEXT NOT NULL,
    insight_source TEXT NOT NULL DEFAULT 'live_fallback',
    generated_by_user_id TEXT,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS file_artifact_id TEXT;

CREATE TABLE IF NOT EXISTS report_generation_jobs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    recording_artifact_id TEXT,
    recording_path TEXT,
    transcript_path TEXT,
    markdown_report_id TEXT,
    pdf_report_id TEXT,
    error_message TEXT,
    requested_by_user_id TEXT,
    claimed_by_worker_id TEXT,
    lease_expires_at TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (markdown_report_id) REFERENCES reports(id) ON DELETE SET NULL,
    FOREIGN KEY (pdf_report_id) REFERENCES reports(id) ON DELETE SET NULL,
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

ALTER TABLE report_generation_jobs
    ADD COLUMN IF NOT EXISTS recording_artifact_id TEXT,
    ADD COLUMN IF NOT EXISTS claimed_by_worker_id TEXT,
    ADD COLUMN IF NOT EXISTS lease_expires_at TEXT,
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;

UPDATE report_generation_jobs
SET attempt_count = 0
WHERE attempt_count IS NULL;

CREATE TABLE IF NOT EXISTS report_shares (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    shared_by_user_id TEXT NOT NULL,
    shared_with_user_id TEXT NOT NULL,
    permission TEXT NOT NULL DEFAULT 'view',
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (shared_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- 호환 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS uq_utterances_session_seq
    ON utterances(session_id, seq_num);

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



