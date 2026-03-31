"""SQLite 스키마 정의."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    mode TEXT NOT NULL,
    source TEXT NOT NULL,
    primary_input_source TEXT,
    actual_active_sources TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS utterances (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    seq_num INTEGER NOT NULL,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    text TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    input_source TEXT,
    stt_backend TEXT,
    latency_ms INTEGER,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS screen_contexts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    captured_at_ms INTEGER NOT NULL,
    ocr_text TEXT,
    title_hint TEXT,
    keywords_json TEXT,
    image_path TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS overlay_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    source_utterance_id TEXT,
    source_screen_id TEXT,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT,
    body TEXT,
    evidence_text TEXT,
    speaker_label TEXT,
    state TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    assignee TEXT,
    due_date TEXT,
    topic_group TEXT,
    input_source TEXT,
    insight_scope TEXT NOT NULL DEFAULT 'live',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id),
    FOREIGN KEY(source_utterance_id) REFERENCES utterances(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    report_type TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    file_path TEXT NOT NULL,
    insight_source TEXT NOT NULL DEFAULT 'live_fallback',
    snapshot_markdown TEXT,
    generated_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_utterances_session_seq
ON utterances(session_id, seq_num);

CREATE UNIQUE INDEX IF NOT EXISTS uq_utterances_session_seq
ON utterances(session_id, seq_num);

CREATE INDEX IF NOT EXISTS idx_screen_contexts_session_time
ON screen_contexts(session_id, captured_at_ms);

CREATE INDEX IF NOT EXISTS idx_overlay_events_session_type
ON overlay_events(session_id, event_type, state);

CREATE INDEX IF NOT EXISTS idx_overlay_events_session_created
ON overlay_events(session_id, created_at_ms);

CREATE INDEX IF NOT EXISTS idx_overlay_events_source_utterance
ON overlay_events(session_id, source_utterance_id, created_at_ms);

CREATE INDEX IF NOT EXISTS idx_reports_session_generated
ON reports(session_id, generated_at);

CREATE INDEX IF NOT EXISTS idx_sessions_status_started
ON sessions(status, started_at);

"""
