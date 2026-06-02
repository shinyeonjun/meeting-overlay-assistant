from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.core.config import settings  # noqa: E402
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID  # noqa: E402
from server.app.infrastructure.artifacts import LocalArtifactStore  # noqa: E402
from server.app.infrastructure.persistence.postgresql.database import (  # noqa: E402
    PostgreSQLDatabase,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_repository import (  # noqa: E402
    PostgreSQLReportRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.retrieval import (  # noqa: E402
    PostgreSQLKnowledgeChunkRepository,
    PostgreSQLKnowledgeDocumentRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session.postgresql_session_repository import (  # noqa: E402
    PostgreSQLSessionRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (  # noqa: E402
    PostgreSQLUtteranceRepository,
)
from server.app.services.reports.query.report_query_service import (  # noqa: E402
    ReportQueryService,
)
from server.app.services.reports.report_models import BuiltMarkdownReport  # noqa: E402
from server.app.services.reports.refinement import TranscriptCorrectionStore  # noqa: E402
from server.app.services.retrieval import (  # noqa: E402
    MarkdownChunker,
    NoteKnowledgeIndexingService,
    OllamaEmbeddingService,
    ReportKnowledgeIndexingService,
    RetrievalQueryService,
)


POSTGRESQL_DIR = (
    PROJECT_ROOT / "server" / "app" / "infrastructure" / "persistence" / "postgresql"
)
DEFAULT_RUNTIME_SCHEMA_PATH = POSTGRESQL_DIR / "000_runtime_compatible_schema.sql"
DEFAULT_INITIAL_SCHEMA_PATH = POSTGRESQL_DIR / "001_initial_schema.sql"
DEFAULT_PGVECTOR_SCHEMA_PATH = POSTGRESQL_DIR / "010_pgvector_knowledge.sql"
DEFAULT_FULL_SCHEMA_PATH = POSTGRESQL_DIR / "020_runtime_with_pgvector_schema.sql"
DEFAULT_TYPED_TARGET_SCHEMA_PATH = (
    POSTGRESQL_DIR / "021_runtime_typed_target_schema.sql"
)
DEFAULT_TYPED_MIGRATION_SCHEMA_PATH = (
    POSTGRESQL_DIR / "022_runtime_typed_inplace_migration.sql"
)

REQUIRED_RUNTIME_TABLES = (
    "sessions",
    "session_participants",
    "participant_followups",
    "utterances",
    "overlay_events",
    "reports",
    "note_correction_jobs",
    "report_generation_jobs",
)

REQUIRED_PGVECTOR_TABLES = (
    "knowledge_documents",
    "knowledge_chunks",
)

REQUIRED_ASSISTANT_CHAT_TABLES = (
    "assistant_conversations",
    "assistant_messages",
    "assistant_response_jobs",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CAPS PostgreSQL 운영 보조 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_schema_parser = subparsers.add_parser(
        "apply-schema",
        help="PostgreSQL에 SQL 스키마를 적용합니다.",
    )
    apply_schema_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    apply_schema_parser.add_argument(
        "--schema",
        choices=("runtime", "initial", "pgvector", "full", "typed-target", "typed-migration"),
        default="runtime",
        help="적용할 스키마 종류",
    )
    apply_schema_parser.add_argument("--schema-path", help="직접 지정한 SQL 파일 경로")

    smoke_parser = subparsers.add_parser(
        "smoke-check",
        help="PostgreSQL 런타임 스키마와 연결 상태를 점검합니다.",
    )
    smoke_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")

    assistant_schema_parser = subparsers.add_parser(
        "ensure-assistant-chat-schema",
        help="assistant conversation/message/job tables만 좁게 준비합니다.",
    )
    assistant_schema_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    assistant_schema_parser.add_argument(
        "--execute",
        action="store_true",
        help="실제로 assistant chat schema를 적용합니다. 생략하면 dry-run입니다.",
    )
    assistant_schema_parser.add_argument(
        "--print-sql",
        action="store_true",
        help="적용할 assistant chat DDL을 출력합니다.",
    )

    backfill_parser = subparsers.add_parser(
        "backfill-report-knowledge",
        help="기존 markdown 회의록을 pgvector knowledge 계층으로 백필합니다.",
    )
    backfill_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    backfill_parser.add_argument(
        "--workspace-id",
        default=DEFAULT_WORKSPACE_ID,
        help="knowledge 적재에 사용할 workspace id",
    )
    backfill_parser.add_argument("--report-id", help="특정 회의록 하나만 백필합니다.")
    backfill_parser.add_argument("--session-id", help="특정 세션의 회의록만 백필합니다.")
    backfill_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="백필할 회의록 수 제한. 생략 시 조건에 맞는 전체를 처리합니다.",
    )

    note_backfill_parser = subparsers.add_parser(
        "backfill-note-knowledge",
        help="기존 세션의 노트 전문을 pgvector knowledge 계층으로 백필합니다.",
    )
    note_backfill_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    note_backfill_parser.add_argument(
        "--workspace-id",
        default=DEFAULT_WORKSPACE_ID,
        help="knowledge 적재에 사용할 workspace id",
    )
    note_backfill_parser.add_argument("--session-id", help="특정 세션의 노트만 백필합니다.")
    note_backfill_parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="백필 후보 세션 수 제한. 기본값은 최근 500개입니다.",
    )
    note_backfill_parser.add_argument(
        "--execute",
        action="store_true",
        help="실제로 knowledge 문서를 생성/교체합니다. 생략하면 dry-run만 수행합니다.",
    )

    prune_parser = subparsers.add_parser(
        "prune-session-summary-knowledge",
        help="session_summary knowledge 문서를 점검하거나 삭제합니다.",
    )
    prune_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    prune_parser.add_argument(
        "--workspace-id",
        default=DEFAULT_WORKSPACE_ID,
        help="정리할 workspace id",
    )
    prune_parser.add_argument(
        "--execute",
        action="store_true",
        help="실제로 knowledge_documents에서 session_summary row를 삭제합니다.",
    )

    retrieval_parser = subparsers.add_parser(
        "search-retrieval",
        help="pgvector hybrid retrieval 결과를 CLI에서 확인합니다.",
    )
    retrieval_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    retrieval_parser.add_argument(
        "--workspace-id",
        default=DEFAULT_WORKSPACE_ID,
        help="검색에 사용할 workspace id",
    )
    retrieval_parser.add_argument("--query", required=True, help="검색 질의")
    retrieval_parser.add_argument("--account-id", help="account 필터")
    retrieval_parser.add_argument("--contact-id", help="contact 필터")
    retrieval_parser.add_argument("--context-thread-id", help="thread 필터")
    retrieval_parser.add_argument("--limit", type=int, default=5, help="반환할 결과 수")

    return parser


def resolve_schema_path(schema: str, schema_path: str | None) -> Path:
    if schema_path:
        return Path(schema_path).resolve()
    if schema == "initial":
        return DEFAULT_INITIAL_SCHEMA_PATH
    if schema == "pgvector":
        return DEFAULT_PGVECTOR_SCHEMA_PATH
    if schema == "full":
        return DEFAULT_FULL_SCHEMA_PATH
    if schema == "typed-target":
        return DEFAULT_TYPED_TARGET_SCHEMA_PATH
    if schema == "typed-migration":
        return DEFAULT_TYPED_MIGRATION_SCHEMA_PATH
    return DEFAULT_RUNTIME_SCHEMA_PATH


def build_database(dsn: str) -> PostgreSQLDatabase:
    normalized = dsn.strip()
    if not normalized:
        raise SystemExit("POSTGRESQL_DSN 또는 --dsn 값을 지정해 주세요.")
    return PostgreSQLDatabase(normalized)


def split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    current_lines: list[str] = []
    in_dollar_block = False
    for line in sql_text.splitlines():
        current_lines.append(line)
        if "$$" in line:
            in_dollar_block = not in_dollar_block
        if not in_dollar_block and line.strip().endswith(";"):
            statement = "\n".join(current_lines).strip()
            if statement:
                statements.append(statement)
            current_lines = []
    tail = "\n".join(current_lines).strip()
    if tail:
        statements.append(tail)
    return statements


def apply_schema(*, database: PostgreSQLDatabase, schema_path: Path) -> None:
    sql_text = schema_path.read_text(encoding="utf-8-sig")
    statements = split_sql_statements(sql_text)
    with database.transaction() as connection:
        for statement in statements:
            if statement.startswith("--") and "\n" not in statement:
                continue
            connection.execute(statement)
    print(f"[OK] 스키마 적용 완료: {schema_path}")


def load_table_counts_postgresql(
    database: PostgreSQLDatabase,
    table_names: tuple[str, ...],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    with database.transaction() as connection:
        for table_name in table_names:
            row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
            counts[table_name] = int(row["total"]) if row is not None else 0
    return counts


def smoke_check(*, database: PostgreSQLDatabase) -> None:
    with database.transaction() as connection:
        version_row = connection.execute("SELECT version() AS version").fetchone()
        table_rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        ).fetchall()

    version = version_row["version"] if version_row is not None else "unknown"
    available_tables = {str(row["table_name"]) for row in table_rows}
    missing_tables = [
        table_name for table_name in REQUIRED_RUNTIME_TABLES if table_name not in available_tables
    ]

    print(f"[OK] PostgreSQL 연결 확인: {version}")
    if missing_tables:
        print("[ERROR] 필수 런타임 테이블이 없습니다:", ", ".join(missing_tables))
        raise SystemExit(1)

    counts = load_table_counts_postgresql(database, REQUIRED_RUNTIME_TABLES)
    print("[OK] 필수 런타임 테이블 점검 완료")
    for table_name, total in counts.items():
        print(f"  - {table_name}: {total}")


def resolve_workspace_identifier_sql_type(database: PostgreSQLDatabase) -> str:
    with database.transaction() as connection:
        row = connection.execute(
            """
            SELECT data_type, udt_name, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'workspaces'
              AND column_name = 'id'
            """
        ).fetchone()
    if row is None:
        raise SystemExit("workspaces.id column을 찾을 수 없습니다. 먼저 runtime schema를 적용해 주세요.")

    udt_name = str(row["udt_name"]).lower()
    data_type = str(row["data_type"]).lower()
    if udt_name == "uuid":
        return "UUID"
    if data_type == "text":
        return "TEXT"
    if data_type == "character varying":
        max_length = row["character_maximum_length"]
        if max_length:
            return f"VARCHAR({int(max_length)})"
        return "VARCHAR"
    raise SystemExit(f"지원하지 않는 workspaces.id column type입니다: {data_type}/{udt_name}")


def build_assistant_chat_schema_sql(identifier_sql_type: str) -> str:
    id_type = identifier_sql_type.strip().upper()
    if not id_type:
        raise ValueError("identifier_sql_type is required")
    return f"""
CREATE TABLE IF NOT EXISTS assistant_conversations (
    id {id_type} PRIMARY KEY,
    workspace_id {id_type} NOT NULL,
    user_id {id_type},
    account_id {id_type},
    contact_id {id_type},
    context_thread_id {id_type},
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    FOREIGN KEY (context_thread_id) REFERENCES context_threads(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS assistant_messages (
    id {id_type} PRIMARY KEY,
    conversation_id {id_type} NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'error')),
    error_message TEXT,
    sources_json JSONB NOT NULL DEFAULT '[]'::JSONB,
    metadata_json JSONB NOT NULL DEFAULT '{{}}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES assistant_conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assistant_response_jobs (
    id {id_type} PRIMARY KEY,
    conversation_id {id_type} NOT NULL,
    user_message_id {id_type} NOT NULL,
    assistant_message_id {id_type} NOT NULL UNIQUE,
    workspace_id {id_type} NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    query TEXT NOT NULL,
    request_json JSONB NOT NULL DEFAULT '{{}}'::JSONB,
    error_message TEXT,
    requested_by_user_id {id_type},
    claimed_by_worker_id TEXT,
    lease_expires_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    FOREIGN KEY (conversation_id) REFERENCES assistant_conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id) REFERENCES assistant_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (assistant_message_id) REFERENCES assistant_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_assistant_conversations_workspace_updated
    ON assistant_conversations(workspace_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_conversations_user_updated
    ON assistant_conversations(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_conversations_context_updated
    ON assistant_conversations(context_thread_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_messages_conversation_created
    ON assistant_messages(conversation_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_assistant_messages_conversation_status
    ON assistant_messages(conversation_id, status);

CREATE INDEX IF NOT EXISTS idx_assistant_response_jobs_conversation_created
    ON assistant_response_jobs(conversation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_response_jobs_status_created
    ON assistant_response_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS idx_assistant_response_jobs_claimable
    ON assistant_response_jobs(status, lease_expires_at, created_at);
"""


def load_existing_tables(database: PostgreSQLDatabase, table_names: tuple[str, ...]) -> set[str]:
    with database.transaction() as connection:
        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            ORDER BY table_name
            """,
            (list(table_names),),
        ).fetchall()
    return {str(row["table_name"]) for row in rows}


def ensure_assistant_chat_schema(
    *,
    database: PostgreSQLDatabase,
    execute: bool,
    print_sql: bool = False,
) -> None:
    identifier_sql_type = resolve_workspace_identifier_sql_type(database)
    existing_before = load_existing_tables(database, REQUIRED_ASSISTANT_CHAT_TABLES)
    missing_before = [
        table_name
        for table_name in REQUIRED_ASSISTANT_CHAT_TABLES
        if table_name not in existing_before
    ]
    sql_text = build_assistant_chat_schema_sql(identifier_sql_type)

    if print_sql:
        print(sql_text.strip())

    if not execute:
        print(
            "[DRY-RUN] assistant chat schema "
            f"id_type={identifier_sql_type} missing_tables={missing_before or 'none'}"
        )
        print("[INFO] 실제 적용은 ensure-assistant-chat-schema --execute 로 실행하세요.")
        return

    statements = split_sql_statements(sql_text)
    with database.transaction() as connection:
        for statement in statements:
            connection.execute(statement)

    existing_after = load_existing_tables(database, REQUIRED_ASSISTANT_CHAT_TABLES)
    missing_after = [
        table_name
        for table_name in REQUIRED_ASSISTANT_CHAT_TABLES
        if table_name not in existing_after
    ]
    if missing_after:
        raise SystemExit(
            "assistant chat schema 적용 후에도 테이블이 없습니다: "
            + ", ".join(missing_after)
        )
    print(
        "[OK] assistant chat schema 적용 완료 "
        f"id_type={identifier_sql_type} tables={', '.join(REQUIRED_ASSISTANT_CHAT_TABLES)}"
    )


def build_embedding_service() -> OllamaEmbeddingService | None:
    backend_name = settings.retrieval_embedding_backend.strip().lower()
    if backend_name == "noop":
        return None
    if backend_name != "ollama":
        raise SystemExit(f"지원하지 않는 retrieval embedding backend입니다: {backend_name}")

    base_url = settings.retrieval_embedding_base_url
    if not base_url:
        raise SystemExit("RETRIEVAL_EMBEDDING_BASE_URL 설정이 필요합니다.")
    return OllamaEmbeddingService(
        base_url=base_url,
        model=settings.retrieval_embedding_model,
        timeout_seconds=settings.retrieval_embedding_timeout_seconds,
        expected_dimensions=settings.retrieval_embedding_dimensions,
    )


def build_report_knowledge_indexing_service(
    database: PostgreSQLDatabase,
) -> ReportKnowledgeIndexingService | None:
    embedding_service = build_embedding_service()
    if embedding_service is None:
        return None

    return ReportKnowledgeIndexingService(
        session_repository=PostgreSQLSessionRepository(database),
        knowledge_document_repository=PostgreSQLKnowledgeDocumentRepository(database),
        knowledge_chunk_repository=PostgreSQLKnowledgeChunkRepository(database),
        embedding_service=embedding_service,
        markdown_chunker=MarkdownChunker(
            target_chars=settings.retrieval_chunk_target_chars,
            overlap_chars=settings.retrieval_chunk_overlap_chars,
        ),
    )


def build_note_knowledge_indexing_service(
    database: PostgreSQLDatabase,
) -> NoteKnowledgeIndexingService | None:
    embedding_service = build_embedding_service()
    if embedding_service is None:
        return None

    return NoteKnowledgeIndexingService(
        session_repository=PostgreSQLSessionRepository(database),
        knowledge_document_repository=PostgreSQLKnowledgeDocumentRepository(database),
        knowledge_chunk_repository=PostgreSQLKnowledgeChunkRepository(database),
        embedding_service=embedding_service,
        markdown_chunker=MarkdownChunker(
            target_chars=settings.retrieval_chunk_target_chars,
            overlap_chars=settings.retrieval_chunk_overlap_chars,
        ),
    )


def build_retrieval_query_service(database: PostgreSQLDatabase) -> RetrievalQueryService | None:
    embedding_service = build_embedding_service()
    if embedding_service is None:
        return None

    return RetrievalQueryService(
        knowledge_chunk_repository=PostgreSQLKnowledgeChunkRepository(database),
        embedding_service=embedding_service,
        candidate_limit=settings.retrieval_search_candidate_limit,
    )


def ensure_pgvector_tables(database: PostgreSQLDatabase) -> None:
    with database.transaction() as connection:
        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        ).fetchall()
    available = {str(row["table_name"]) for row in rows}
    missing = [name for name in REQUIRED_PGVECTOR_TABLES if name not in available]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            f"pgvector 테이블이 없습니다: {joined}. "
            "먼저 apply-schema --schema pgvector를 실행해 주세요.",
        )


def iter_target_reports(
    *,
    report_repository: PostgreSQLReportRepository,
    report_id: str | None,
    session_id: str | None,
    limit: int | None,
):
    if report_id:
        report = report_repository.get_by_id(report_id)
        if report is None:
            raise SystemExit(f"지정한 회의록을 찾을 수 없습니다: {report_id}")
        reports = [report]
    elif session_id:
        reports = report_repository.list_by_session(session_id)
    else:
        reports = report_repository.list_recent(limit=limit)

    emitted = 0
    for report in reports:
        if report.report_type != "markdown":
            continue
        yield report
        emitted += 1
        if limit is not None and emitted >= limit:
            return


def backfill_report_knowledge(
    *,
    database: PostgreSQLDatabase,
    workspace_id: str,
    report_id: str | None,
    session_id: str | None,
    limit: int | None,
) -> None:
    ensure_pgvector_tables(database)
    report_repository = PostgreSQLReportRepository(database)
    report_query_service = ReportQueryService(report_repository)
    indexing_service = build_report_knowledge_indexing_service(database)
    if indexing_service is None:
        print("[SKIP] RETRIEVAL_EMBEDDING_BACKEND=noop 이므로 report knowledge backfill을 건너뜁니다.")
        return

    total = 0
    indexed = 0
    skipped = 0
    failed = 0

    for report in iter_target_reports(
        report_repository=report_repository,
        report_id=report_id,
        session_id=session_id,
        limit=limit,
    ):
        total += 1
        try:
            content = report_query_service.read_report_content(report)
        except FileNotFoundError:
            skipped += 1
            reference = report.file_artifact_id or report.file_path
            print(f"[SKIP] {report.id}: markdown 파일 경로를 찾을 수 없습니다. ({reference})")
            continue

        try:
            if not content or not content.strip():
                skipped += 1
                print(f"[SKIP] {report.id}: markdown 본문이 비어 있습니다.")
                continue

            built_report = BuiltMarkdownReport(
                report=report,
                content=content,
                speaker_transcript=[],
                speaker_events=[],
            )
            document = indexing_service.index_markdown_report(
                built_report,
                workspace_id=workspace_id,
            )
            if document is None:
                skipped += 1
                print(f"[SKIP] {report.id}: knowledge 문서로 변환할 내용이 없습니다.")
                continue

            indexed += 1
            print(f"[OK] {report.id} -> {document.id}")
        except Exception as error:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {report.id}: {error}")

    print(
        "[DONE] report knowledge backfill "
        f"(total={total}, indexed={indexed}, skipped={skipped}, failed={failed})",
    )
    if failed:
        raise SystemExit(3)


def iter_target_sessions(
    *,
    session_repository: PostgreSQLSessionRepository,
    session_id: str | None,
    limit: int,
):
    if session_id:
        session = session_repository.get_by_id(session_id)
        if session is None:
            raise SystemExit(f"지정한 세션을 찾을 수 없습니다: {session_id}")
        yield session
        return

    for session in session_repository.list_recent(limit=max(1, limit)):
        yield session


def backfill_note_knowledge(
    *,
    database: PostgreSQLDatabase,
    workspace_id: str,
    session_id: str | None,
    limit: int,
    execute: bool,
) -> None:
    ensure_pgvector_tables(database)
    session_repository = PostgreSQLSessionRepository(database)
    utterance_repository = PostgreSQLUtteranceRepository(database)
    correction_store = TranscriptCorrectionStore(
        LocalArtifactStore(settings.artifacts_root_path)
    )
    indexing_service = build_note_knowledge_indexing_service(database) if execute else None
    if execute and indexing_service is None:
        print("[SKIP] RETRIEVAL_EMBEDDING_BACKEND=noop 이므로 note knowledge backfill을 건너뜁니다.")
        return

    total = 0
    indexed = 0
    dry_run = 0
    skipped = 0
    failed = 0

    for session in iter_target_sessions(
        session_repository=session_repository,
        session_id=session_id,
        limit=limit,
    ):
        total += 1
        utterances = utterance_repository.list_by_session(session.id)
        if not utterances:
            skipped += 1
            print(f"[SKIP] {session.id}: 저장된 utterance가 없습니다.")
            continue

        source_version = max(0, int(session.canonical_transcript_version or 0))
        correction_document = correction_store.load(
            session_id=session.id,
            expected_source_version=source_version,
        )
        corrected = correction_document is not None

        if not execute:
            dry_run += 1
            print(
                f"[DRY-RUN] {session.id}: title={session.title!r} "
                f"utterances={len(utterances)} source_version={source_version} "
                f"correction={'yes' if corrected else 'no'}"
            )
            continue

        try:
            document = indexing_service.index_note_transcript(
                session_id=session.id,
                source_version=source_version,
                utterances=utterances,
                correction_document=correction_document,
                workspace_id=workspace_id,
            )
            if document is None:
                skipped += 1
                print(f"[SKIP] {session.id}: knowledge 문서로 변환할 노트 본문이 없습니다.")
                continue

            indexed += 1
            print(f"[OK] {session.id} -> {document.id}")
        except Exception as error:  # noqa: BLE001
            failed += 1
            print(f"[ERROR] {session.id}: {error}")

    mode = "execute" if execute else "dry-run"
    print(
        "[DONE] note knowledge backfill "
        f"mode={mode} total={total}, indexed={indexed}, dry_run={dry_run}, "
        f"skipped={skipped}, failed={failed}"
    )
    if failed:
        raise SystemExit(3)


def load_session_summary_knowledge_counts(
    *,
    database: PostgreSQLDatabase,
    workspace_id: str,
) -> tuple[int, int]:
    with database.transaction() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(DISTINCT kd.id) AS document_count,
                COALESCE(COUNT(kc.id), 0) AS chunk_count
            FROM knowledge_documents kd
            LEFT JOIN knowledge_chunks kc ON kc.document_id = kd.id
            WHERE kd.workspace_id = %s
              AND kd.source_type = 'session_summary'
            """,
            (workspace_id,),
        ).fetchone()
    if row is None:
        return 0, 0
    return int(row["document_count"] or 0), int(row["chunk_count"] or 0)


def prune_session_summary_knowledge(
    *,
    database: PostgreSQLDatabase,
    workspace_id: str,
    execute: bool,
) -> None:
    ensure_pgvector_tables(database)
    document_count, chunk_count = load_session_summary_knowledge_counts(
        database=database,
        workspace_id=workspace_id,
    )
    if not execute:
        print(
            "[DRY-RUN] session_summary knowledge 정리 대상 "
            f"documents={document_count}, chunks={chunk_count}"
        )
        print("[INFO] 실제 삭제는 --execute를 붙여 다시 실행해 주세요.")
        return

    with database.transaction() as connection:
        deleted_rows = connection.execute(
            """
            DELETE FROM knowledge_documents
            WHERE workspace_id = %s
              AND source_type = 'session_summary'
            RETURNING id
            """,
            (workspace_id,),
        ).fetchall()
    print(
        "[DONE] session_summary knowledge 삭제 완료 "
        f"documents={len(deleted_rows)}, cascaded_chunks_before_delete={chunk_count}"
    )


def search_retrieval(
    *,
    database: PostgreSQLDatabase,
    workspace_id: str,
    query: str,
    account_id: str | None,
    contact_id: str | None,
    context_thread_id: str | None,
    limit: int,
) -> None:
    ensure_pgvector_tables(database)
    retrieval_query_service = build_retrieval_query_service(database)
    if retrieval_query_service is None:
        print("[SKIP] RETRIEVAL_EMBEDDING_BACKEND=noop 이므로 retrieval search를 실행하지 않습니다.")
        return

    items = retrieval_query_service.search(
        workspace_id=workspace_id,
        query=query,
        account_id=account_id,
        contact_id=contact_id,
        context_thread_id=context_thread_id,
        limit=limit,
    )
    print(f"[OK] retrieval result_count={len(items)}")
    for index, item in enumerate(items, start=1):
        preview = item.chunk_text.replace("\r", " ").replace("\n", " ").strip()
        if len(preview) > 120:
            preview = preview[:117] + "..."
        print(
            f"  {index}. distance={item.distance:.4f} "
            f"document_id={item.document_id} source={item.source_type}:{item.source_id}",
        )
        print(f"     title={item.document_title}")
        print(f"     chunk={preview}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "apply-schema":
        database = build_database(args.dsn)
        schema_path = resolve_schema_path(args.schema, args.schema_path)
        apply_schema(database=database, schema_path=schema_path)
        return

    if args.command == "smoke-check":
        database = build_database(args.dsn)
        smoke_check(database=database)
        return

    if args.command == "ensure-assistant-chat-schema":
        database = build_database(args.dsn)
        ensure_assistant_chat_schema(
            database=database,
            execute=bool(args.execute),
            print_sql=bool(args.print_sql),
        )
        return

    if args.command == "backfill-report-knowledge":
        database = build_database(args.dsn)
        backfill_report_knowledge(
            database=database,
            workspace_id=args.workspace_id,
            report_id=args.report_id,
            session_id=args.session_id,
            limit=args.limit,
        )
        return

    if args.command == "backfill-note-knowledge":
        database = build_database(args.dsn)
        backfill_note_knowledge(
            database=database,
            workspace_id=args.workspace_id,
            session_id=args.session_id,
            limit=max(1, args.limit),
            execute=bool(args.execute),
        )
        return

    if args.command == "prune-session-summary-knowledge":
        database = build_database(args.dsn)
        prune_session_summary_knowledge(
            database=database,
            workspace_id=args.workspace_id,
            execute=bool(args.execute),
        )
        return

    if args.command == "search-retrieval":
        database = build_database(args.dsn)
        search_retrieval(
            database=database,
            workspace_id=args.workspace_id,
            query=args.query,
            account_id=args.account_id,
            contact_id=args.contact_id,
            context_thread_id=args.context_thread_id,
            limit=max(1, args.limit),
        )
        return

    raise SystemExit(f"지원하지 않는 명령입니다: {args.command}")


if __name__ == "__main__":
    main()
