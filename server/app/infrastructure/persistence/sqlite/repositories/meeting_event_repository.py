"""이전 SQLite 이벤트 저장소 경로 호환용 shim."""

from server.app.infrastructure.persistence.sqlite.repositories.events.sqlite_event_repository import (
    SQLiteMeetingEventRepository,
)

__all__ = ["SQLiteMeetingEventRepository"]
