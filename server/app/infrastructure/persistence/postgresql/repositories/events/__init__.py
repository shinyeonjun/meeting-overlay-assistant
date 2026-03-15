"""PostgreSQL 이벤트 저장소 모음."""

from server.app.infrastructure.persistence.postgresql.repositories.events.postgresql_event_repository import (
    PostgreSQLMeetingEventRepository,
)

__all__ = ["PostgreSQLMeetingEventRepository"]
