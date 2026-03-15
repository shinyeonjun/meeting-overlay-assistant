from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.core.config import settings  # noqa: E402
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID  # noqa: E402
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
from server.app.services.reports.query.report_query_service import (  # noqa: E402
    ReportQueryService,
)
from server.app.services.reports.report_models import BuiltMarkdownReport  # noqa: E402
from server.app.services.retrieval import (  # noqa: E402
    MarkdownChunker,
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
DEFAULT_SQLITE_PATH = PROJECT_ROOT / settings.database_path

TABLE_MIGRATION_ORDER = (
    "workspaces",
    "users",
    "workspace_members",
    "auth_password_credentials",
    "auth_sessions",
    "accounts",
    "contacts",
    "context_threads",
    "sessions",
    "session_participants",
    "participant_followups",
    "utterances",
    "overlay_events",
    "reports",
    "report_generation_jobs",
    "report_shares",
)

JSONB_COLUMNS: dict[str, set[str]] = {
    "sessions": {"actual_active_sources"},
}

REQUIRED_RUNTIME_TABLES = (
    "sessions",
    "session_participants",
    "participant_followups",
    "utterances",
    "overlay_events",
    "reports",
    "report_generation_jobs",
)

REQUIRED_PGVECTOR_TABLES = (
    "knowledge_documents",
    "knowledge_chunks",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CAPS PostgreSQL 운영 보조 스크립트")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_schema_parser = subparsers.add_parser(
        "apply-schema",
        help="PostgreSQL에 SQL 스키마를 적용합니다.",
    )
    apply_schema_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    apply_schema_parser.add_argument(
        "--schema",
        choices=("runtime", "initial", "pgvector", "full"),
        default="runtime",
        help="적용할 스키마 종류",
    )
    apply_schema_parser.add_argument("--schema-path", help="직접 지정한 SQL 파일 경로")

    migrate_parser = subparsers.add_parser(
        "migrate-sqlite",
        help="SQLite 데이터를 PostgreSQL로 복사합니다.",
    )
    migrate_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    migrate_parser.add_argument(
        "--sqlite-path",
        default=str(DEFAULT_SQLITE_PATH),
        help="원본 SQLite 경로",
    )
    migrate_parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="복사 전에 PostgreSQL 대상 테이블을 비웁니다.",
    )
    migrate_parser.add_argument("--tables", nargs="*", help="특정 테이블만 복사합니다.")

    smoke_parser = subparsers.add_parser(
        "smoke-check",
        help="PostgreSQL 스모크 체크를 수행합니다.",
    )
    smoke_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    smoke_parser.add_argument(
        "--sqlite-path",
        default="",
        help="비교용 SQLite 경로. 주면 row count를 비교합니다.",
    )

    backfill_parser = subparsers.add_parser(
        "backfill-report-knowledge",
        help="기존 markdown 리포트를 pgvector knowledge 계층으로 백필합니다.",
    )
    backfill_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")
    backfill_parser.add_argument(
        "--workspace-id",
        default=DEFAULT_WORKSPACE_ID,
        help="knowledge 적재에 사용할 workspace id",
    )
    backfill_parser.add_argument("--report-id", help="특정 리포트 하나만 백필합니다.")
    backfill_parser.add_argument("--session-id", help="특정 세션의 리포트만 백필합니다.")
    backfill_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="백필할 리포트 수. 생략하면 조건에 맞는 전체를 백필합니다.",
    )

    retrieval_parser = subparsers.add_parser(
        "search-retrieval",
        help="pgvector hybrid retrieval 검색 결과를 바로 확인합니다.",
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
    return DEFAULT_RUNTIME_SCHEMA_PATH


def build_database(dsn: str) -> PostgreSQLDatabase:
    normalized = dsn.strip()
    if not normalized:
        raise SystemExit("POSTGRESQL_DSN 또는 --dsn 값을 지정해야 합니다.")
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


def connect_sqlite(sqlite_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def get_sqlite_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(row["name"]) for row in rows]


def sqlite_table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def get_postgresql_columns(database: PostgreSQLDatabase, table_name: str) -> list[str]:
    with database.transaction() as connection:
        rows = connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position ASC
            """,
            (table_name,),
        ).fetchall()
    return [str(row["column_name"]) for row in rows]


def normalize_json_value(raw_value: object) -> str:
    if raw_value is None:
        return "null"
    if isinstance(raw_value, (dict, list)):
        return json.dumps(raw_value, ensure_ascii=False)
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            return "null"
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            return json.dumps(raw_value, ensure_ascii=False)
    return json.dumps(raw_value, ensure_ascii=False)


def build_insert_sql(table_name: str, columns: Iterable[str]) -> str:
    column_list = list(columns)
    placeholders: list[str] = []
    jsonb_columns = JSONB_COLUMNS.get(table_name, set())
    for column_name in column_list:
        if column_name in jsonb_columns:
            placeholders.append("%s::jsonb")
        else:
            placeholders.append("%s")
    joined_columns = ", ".join(column_list)
    joined_placeholders = ", ".join(placeholders)
    return f"INSERT INTO {table_name} ({joined_columns}) VALUES ({joined_placeholders})"


def truncate_tables(database: PostgreSQLDatabase, table_names: Iterable[str]) -> None:
    ordered = list(table_names)
    if not ordered:
        return
    joined = ", ".join(reversed(ordered))
    with database.transaction() as connection:
        connection.execute(f"TRUNCATE TABLE {joined} CASCADE")
    print(f"[OK] 대상 테이블 비움: {len(ordered)}개")


def migrate_table(
    *,
    sqlite_connection: sqlite3.Connection,
    database: PostgreSQLDatabase,
    table_name: str,
) -> tuple[int, list[str]]:
    sqlite_columns = get_sqlite_columns(sqlite_connection, table_name)
    postgresql_columns = get_postgresql_columns(database, table_name)
    columns = [column for column in sqlite_columns if column in postgresql_columns]
    if not columns:
        return 0, []

    sqlite_rows = sqlite_connection.execute(f"SELECT * FROM {table_name}").fetchall()
    if not sqlite_rows:
        return 0, columns

    insert_sql = build_insert_sql(table_name, columns)
    jsonb_columns = JSONB_COLUMNS.get(table_name, set())
    values: list[tuple[object, ...]] = []
    for row in sqlite_rows:
        item: list[object] = []
        for column_name in columns:
            raw_value = row[column_name]
            if column_name in jsonb_columns:
                item.append(normalize_json_value(raw_value))
            else:
                item.append(raw_value)
        values.append(tuple(item))

    with database.transaction() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(insert_sql, values)
    return len(values), columns


def migrate_sqlite_to_postgresql(
    *,
    sqlite_path: Path,
    database: PostgreSQLDatabase,
    table_names: Iterable[str],
    truncate_target: bool,
) -> None:
    tables = [name for name in table_names if name]
    if truncate_target:
        truncate_tables(database, tables)

    sqlite_connection = connect_sqlite(sqlite_path)
    try:
        for table_name in tables:
            if not sqlite_table_exists(sqlite_connection, table_name):
                print(f"[SKIP] {table_name}: SQLite 원본에 테이블이 없습니다.")
                continue
            copied, columns = migrate_table(
                sqlite_connection=sqlite_connection,
                database=database,
                table_name=table_name,
            )
            suffix = f" ({', '.join(columns)})" if columns else ""
            print(f"[OK] {table_name}: {copied} rows copied{suffix}")
    finally:
        sqlite_connection.close()


def load_table_counts_sqlite(sqlite_path: Path, table_names: Iterable[str]) -> dict[str, int]:
    sqlite_connection = connect_sqlite(sqlite_path)
    try:
        counts: dict[str, int] = {}
        for table_name in table_names:
            if not sqlite_table_exists(sqlite_connection, table_name):
                counts[table_name] = 0
                continue
            row = sqlite_connection.execute(
                f"SELECT COUNT(*) AS total FROM {table_name}",
            ).fetchone()
            counts[table_name] = int(row["total"]) if row is not None else 0
        return counts
    finally:
        sqlite_connection.close()


def load_table_counts_postgresql(
    database: PostgreSQLDatabase,
    table_names: Iterable[str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    with database.transaction() as connection:
        for table_name in table_names:
            row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
            counts[table_name] = int(row["total"]) if row is not None else 0
    return counts


def smoke_check(*, database: PostgreSQLDatabase, sqlite_path: Path | None) -> None:
    with database.transaction() as connection:
        row = connection.execute("SELECT version() AS version").fetchone()
        version = row["version"] if row is not None else "unknown"
        table_rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        ).fetchall()
    available_tables = {str(row["table_name"]) for row in table_rows}
    missing_tables = [
        table_name for table_name in REQUIRED_RUNTIME_TABLES if table_name not in available_tables
    ]

    print(f"[OK] PostgreSQL 연결 확인: {version}")
    if missing_tables:
        print("[ERROR] 필수 런타임 테이블이 없습니다:", ", ".join(missing_tables))
        raise SystemExit(1)

    postgresql_counts = load_table_counts_postgresql(database, REQUIRED_RUNTIME_TABLES)
    print("[OK] 필수 런타임 테이블 확인 완료")
    for table_name, total in postgresql_counts.items():
        print(f"  - {table_name}: {total}")

    if sqlite_path is None:
        return

    sqlite_counts = load_table_counts_sqlite(sqlite_path, REQUIRED_RUNTIME_TABLES)
    print("[INFO] SQLite 대비 row count 비교")
    mismatch_found = False
    for table_name in REQUIRED_RUNTIME_TABLES:
        sqlite_total = sqlite_counts[table_name]
        postgresql_total = postgresql_counts[table_name]
        marker = "OK" if sqlite_total == postgresql_total else "DIFF"
        mismatch_found = mismatch_found or marker == "DIFF"
        print(f"  - {table_name}: sqlite={sqlite_total} postgresql={postgresql_total} [{marker}]")
    if mismatch_found:
        raise SystemExit(2)


def build_embedding_service() -> OllamaEmbeddingService:
    base_url = settings.retrieval_embedding_base_url
    if not base_url:
        raise SystemExit("RETRIEVAL_EMBEDDING_BASE_URL 설정이 필요합니다.")
    return OllamaEmbeddingService(
        base_url=base_url,
        model=settings.retrieval_embedding_model,
        timeout_seconds=settings.retrieval_embedding_timeout_seconds,
    )


def build_report_knowledge_indexing_service(
    database: PostgreSQLDatabase,
) -> ReportKnowledgeIndexingService:
    return ReportKnowledgeIndexingService(
        session_repository=PostgreSQLSessionRepository(database),
        knowledge_document_repository=PostgreSQLKnowledgeDocumentRepository(database),
        knowledge_chunk_repository=PostgreSQLKnowledgeChunkRepository(database),
        embedding_service=build_embedding_service(),
        markdown_chunker=MarkdownChunker(
            target_chars=settings.retrieval_chunk_target_chars,
            overlap_chars=settings.retrieval_chunk_overlap_chars,
        ),
    )


def build_retrieval_query_service(database: PostgreSQLDatabase) -> RetrievalQueryService:
    return RetrievalQueryService(
        knowledge_chunk_repository=PostgreSQLKnowledgeChunkRepository(database),
        embedding_service=build_embedding_service(),
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
            "먼저 apply-schema --schema pgvector를 실행해 주세요."
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
            raise SystemExit(f"지정한 리포트를 찾을 수 없습니다: {report_id}")
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
            print(f"[SKIP] {report.id}: markdown 파일 경로를 찾을 수 없습니다. ({report.file_path})")
            continue
        try:
            if not content or not content.strip():
                skipped += 1
                print(f"[SKIP] {report.id}: markdown 본문이 없습니다.")
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
        except Exception as error:
            failed += 1
            print(f"[ERROR] {report.id}: {error}")

    print(
        "[DONE] report knowledge backfill "
        f"(total={total}, indexed={indexed}, skipped={skipped}, failed={failed})"
    )
    if failed:
        raise SystemExit(3)


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
            f"document_id={item.document_id} source={item.source_type}:{item.source_id}"
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

    if args.command == "migrate-sqlite":
        database = build_database(args.dsn)
        sqlite_path = Path(args.sqlite_path).resolve()
        table_names = tuple(args.tables) if args.tables else TABLE_MIGRATION_ORDER
        migrate_sqlite_to_postgresql(
            sqlite_path=sqlite_path,
            database=database,
            table_names=table_names,
            truncate_target=args.truncate_target,
        )
        return

    if args.command == "smoke-check":
        database = build_database(args.dsn)
        sqlite_path = Path(args.sqlite_path).resolve() if args.sqlite_path else None
        smoke_check(database=database, sqlite_path=sqlite_path)
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
