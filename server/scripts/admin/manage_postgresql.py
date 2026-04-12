from __future__ import annotations

import argparse
import sys
from pathlib import Path


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
    parser = argparse.ArgumentParser(description="CAPS PostgreSQL 운영 보조 CLI")
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

    smoke_parser = subparsers.add_parser(
        "smoke-check",
        help="PostgreSQL 런타임 스키마와 연결 상태를 점검합니다.",
    )
    smoke_parser.add_argument("--dsn", default=settings.postgresql_dsn or "", help="PostgreSQL DSN")

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
        help="백필할 리포트 수 제한. 생략 시 조건에 맞는 전체를 처리합니다.",
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
