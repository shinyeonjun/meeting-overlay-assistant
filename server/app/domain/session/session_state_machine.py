"""세션 상태 전이 규칙."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from server.app.domain.shared.enums import SessionStatus
from server.app.core.clock import utc_now_iso

if TYPE_CHECKING:
    from server.app.domain.session.meeting_session import MeetingSession




def start_meeting_session(session: "MeetingSession") -> "MeetingSession":
    """draft 세션을 running 상태로 전이한다."""

    if session.status == SessionStatus.RUNNING:
        return session
    if session.status == SessionStatus.ENDED:
        raise ValueError("이미 종료된 세션은 다시 시작할 수 없습니다.")

    return replace(
        session,
        status=SessionStatus.RUNNING,
        started_at=utc_now_iso(),
        ended_at=None,
        actual_active_sources=(),
    )


def end_meeting_session(session: "MeetingSession") -> "MeetingSession":
    """세션을 ended 상태로 전이한다."""

    if session.status == SessionStatus.ENDED:
        return session
    return replace(session, status=SessionStatus.ENDED, ended_at=utc_now_iso())
