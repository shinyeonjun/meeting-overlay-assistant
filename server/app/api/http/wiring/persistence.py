"""PostgreSQL 저장소 조립과 초기 검증을 담당한다."""

from __future__ import annotations

import logging
from functools import lru_cache
from urllib.parse import urlsplit

from server.app.core.config import settings
from server.app.infrastructure.persistence.postgresql import PostgreSQLDatabase
from server.app.infrastructure.persistence.postgresql.repositories import (
    PostgreSQLAuthRepository,
    PostgreSQLKnowledgeChunkRepository,
    PostgreSQLKnowledgeDocumentRepository,
    PostgreSQLMeetingContextRepository,
    PostgreSQLMeetingEventRepository,
    PostgreSQLParticipantFollowupRepository,
    PostgreSQLReportGenerationJobRepository,
    PostgreSQLReportRepository,
    PostgreSQLReportShareRepository,
    PostgreSQLSessionPostProcessingJobRepository,
    PostgreSQLSessionRepository,
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.auth_helpers.workspace import (
    ensure_default_workspace,
)


logger = logging.getLogger(__name__)

REQUIRED_RUNTIME_TABLES = (
    "workspaces",
    "users",
    "workspace_members",
    "auth_password_credentials",
    "auth_sessions",
    "sessions",
    "session_participants",
    "participant_followups",
    "utterances",
    "overlay_events",
    "reports",
    "session_post_processing_jobs",
    "report_generation_jobs",
)


@lru_cache(maxsize=1)
def get_postgresql_database() -> PostgreSQLDatabase:
    """PostgreSQL 데이터베이스 객체를 캐시한다."""

    if not settings.postgresql_dsn:
        raise RuntimeError("POSTGRESQL_DSN 설정이 필요합니다.")
    return PostgreSQLDatabase(settings.postgresql_dsn)


def get_transaction_manager():
    """트랜잭션 매니저를 반환한다."""

    return get_postgresql_database()


def describe_primary_persistence_target() -> str:
    """현재 persistence target을 로그 친화 문자열로 반환한다."""

    return _describe_postgresql_dsn(settings.postgresql_dsn)


def initialize_primary_persistence() -> None:
    """PostgreSQL 연결과 핵심 런타임 스키마 준비 상태를 확인한다."""

    postgresql_database = get_postgresql_database()
    with postgresql_database.transaction() as connection:
        connection.execute("SELECT 1")
        ensure_default_workspace(connection)
        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        ).fetchall()

    available_tables = {str(row["table_name"]) for row in rows}
    missing_tables = [
        table_name for table_name in REQUIRED_RUNTIME_TABLES if table_name not in available_tables
    ]
    if missing_tables:
        joined = ", ".join(missing_tables)
        raise RuntimeError(
            "PostgreSQL 런타임 스키마가 비어 있거나 불완전합니다. "
            f"누락 테이블: {joined}. "
            "먼저 "
            r"`D:\caps\venv\Scripts\python.exe server\scripts\admin\manage_postgresql.py apply-schema --schema full` "
            "을 실행해 주세요.",
        )

    logger.info("PostgreSQL 연결 및 런타임 스키마 확인 완료")


def get_auth_repository():
    """인증 저장소를 반환한다."""

    return PostgreSQLAuthRepository(get_postgresql_database())


def get_meeting_context_repository():
    """미팅 컨텍스트 저장소를 반환한다."""

    return PostgreSQLMeetingContextRepository(get_postgresql_database())


def get_session_repository():
    """세션 저장소를 반환한다."""

    return PostgreSQLSessionRepository(get_postgresql_database())


def get_participant_followup_repository():
    """참여자 후속 작업 저장소를 반환한다."""

    return PostgreSQLParticipantFollowupRepository(get_postgresql_database())


def get_event_repository():
    """이벤트 저장소를 반환한다."""

    return PostgreSQLMeetingEventRepository(get_postgresql_database())


def get_utterance_repository():
    """발화 저장소를 반환한다."""

    return PostgreSQLUtteranceRepository(get_postgresql_database())


def get_report_repository():
    """리포트 저장소를 반환한다."""

    return PostgreSQLReportRepository(get_postgresql_database())


def get_report_generation_job_repository():
    """리포트 생성 job 저장소를 반환한다."""

    return PostgreSQLReportGenerationJobRepository(get_postgresql_database())


def get_session_post_processing_job_repository():
    """세션 후처리 job 저장소를 반환한다."""

    return PostgreSQLSessionPostProcessingJobRepository(get_postgresql_database())


def get_report_share_repository():
    """리포트 공유 저장소를 반환한다."""

    return PostgreSQLReportShareRepository(get_postgresql_database())


def get_knowledge_document_repository():
    """knowledge document 저장소를 반환한다."""

    return PostgreSQLKnowledgeDocumentRepository(get_postgresql_database())


def get_knowledge_chunk_repository():
    """knowledge chunk 저장소를 반환한다."""

    return PostgreSQLKnowledgeChunkRepository(get_postgresql_database())


def _describe_postgresql_dsn(dsn: str | None) -> str:
    """비밀번호를 가린 PostgreSQL DSN 요약을 만든다."""

    if not dsn:
        return "postgresql://(미설정)"

    parsed = urlsplit(dsn)
    hostname = parsed.hostname or "localhost"
    port = f":{parsed.port}" if parsed.port else ""
    database_name = parsed.path.lstrip("/") or "(default)"
    username = parsed.username or "unknown"
    return f"postgresql://{username}@{hostname}{port}/{database_name}"
