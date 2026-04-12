"""이전 이벤트 저장소 경로 호환용 shim."""

from server.app.repositories.contracts.events.event_repository import MeetingEventRepository

__all__ = ["MeetingEventRepository"]
