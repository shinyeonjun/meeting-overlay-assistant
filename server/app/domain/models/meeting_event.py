"""이전 meeting_event 경로 호환용 shim."""

from server.app.domain.events.meeting_event import MeetingEvent

__all__ = ["MeetingEvent"]
