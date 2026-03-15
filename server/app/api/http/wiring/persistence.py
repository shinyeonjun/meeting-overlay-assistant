"""현재 persistence backend 선택과 저장소 조립."""

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
    PostgreSQLSessionRepository,
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.sqlite.database import database as sqlite_database
from server.app.infrastructure.persistence.sqlite.repositories.auth_repository import (
    SQLiteAuthRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.meeting_context_repository import (
    SQLiteMeetingContextRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.meeting_event_repository import (
    SQLiteMeetingEventRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.participation import (
    SQLiteParticipantFollowupRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.report_generation_job_repository import (
    SQLiteReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.report_repository import (
    SQLiteReportRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.report_share_repository import (
    SQLiteReportShareRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.session import (
    SQLiteSessionRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.utterance_repository import (
    SQLiteUtteranceRepository,
)

logger = logging.getLogger(__name__)

# 테스트 격리를 위해 SQLite backend의 database 인스턴스를 교체할 수 있게 둔다.
database = sqlite_database


def get_persistence_backend() -> str:
    """현재 설정된 persistence backend를 반환한다."""

    return settings.persistence_backend.strip().lower()


def is_postgresql_backend() -> bool:
    """PostgreSQL backend 사용 여부를 반환한다."""

    return get_persistence_backend() == "postgresql"


def get_sqlite_database():
    """현재 설정된 SQLite database 인스턴스를 반환한다."""

    return database


@lru_cache(maxsize=1)
def get_postgresql_database() -> PostgreSQLDatabase:
    """PostgreSQL 데이터베이스 객체를 캐시한다."""

    if not settings.postgresql_dsn:
        raise RuntimeError(
            "PERSISTENCE_BACKEND=postgresql 인 경우 POSTGRESQL_DSN 설정이 필요합니다.",
        )
    return PostgreSQLDatabase(settings.postgresql_dsn)


def get_transaction_manager():
    """현재 backend에 맞는 트랜잭션 매니저를 반환한다."""

    if is_postgresql_backend():
        return get_postgresql_database()
    return get_sqlite_database()


def describe_primary_persistence_target() -> str:
    """현재 persistence target을 로그 친화 문자열로 반환한다."""

    if is_postgresql_backend():
        return _describe_postgresql_dsn(settings.postgresql_dsn)
    return str(get_sqlite_database().database_path)


def initialize_primary_persistence() -> None:
    """현재 backend를 초기 준비한다."""

    if is_postgresql_backend():
        postgresql_database = get_postgresql_database()
        with postgresql_database.transaction() as connection:
            connection.execute("SELECT 1")
        logger.info("PostgreSQL 연결 확인 완료")
        return

    get_sqlite_database().initialize()


def get_auth_repository():
    """인증 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLAuthRepository(get_postgresql_database())
    return SQLiteAuthRepository(get_sqlite_database())


def get_meeting_context_repository():
    """맥락 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLMeetingContextRepository(get_postgresql_database())
    return SQLiteMeetingContextRepository(get_sqlite_database())


def get_session_repository():
    """세션 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLSessionRepository(get_postgresql_database())
    return SQLiteSessionRepository(get_sqlite_database())


def get_participant_followup_repository():
    """참여자 후속 작업 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLParticipantFollowupRepository(get_postgresql_database())
    return SQLiteParticipantFollowupRepository(get_sqlite_database())


def get_event_repository():
    """이벤트 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLMeetingEventRepository(get_postgresql_database())
    return SQLiteMeetingEventRepository(get_sqlite_database())


def get_utterance_repository():
    """발화 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLUtteranceRepository(get_postgresql_database())
    return SQLiteUtteranceRepository(get_sqlite_database())


def get_report_repository():
    """리포트 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLReportRepository(get_postgresql_database())
    return SQLiteReportRepository(get_sqlite_database())


def get_report_generation_job_repository():
    """리포트 생성 job 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLReportGenerationJobRepository(get_postgresql_database())
    return SQLiteReportGenerationJobRepository(get_sqlite_database())


def get_report_share_repository():
    """리포트 공유 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLReportShareRepository(get_postgresql_database())
    return SQLiteReportShareRepository(get_sqlite_database())


def get_knowledge_document_repository():
    """knowledge document 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLKnowledgeDocumentRepository(get_postgresql_database())
    return None


def get_knowledge_chunk_repository():
    """knowledge chunk 저장소를 반환한다."""

    if is_postgresql_backend():
        return PostgreSQLKnowledgeChunkRepository(get_postgresql_database())
    return None


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
